"""
Share the city cache between machines through the git remote.

The cache lives in the repository, so both machines keep adding to their own
copy. Pushing one over the other would throw away everything the other machine
looked up, so this merges them first: every coordinate key from both sides is
kept, and when the same key exists on both, the newer timestamp wins.

Only `cache/city_cache.json` is committed; nothing else in the working tree is
touched.
"""

import json
import os
import platform
import subprocess
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

# Path of the cache inside the repository (git always uses forward slashes).
CACHE_REL_PATH = 'cache/city_cache.json'

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(REPO_DIR, 'cache', 'city_cache.json')


@dataclass
class SyncResult:
    """Outcome of a cache sync."""
    success: bool
    message: str
    gained: int = 0        # entries the remote had and we did not
    contributed: int = 0   # entries we had and the remote did not
    pushed: bool = False
    details: str = ''


def _git(repo_dir: str, *args: str, timeout: int = 120) -> Tuple[int, str, str]:
    """Run a git command in the repository; returns (code, stdout, stderr)."""
    proc = subprocess.run(['git', *args], cwd=repo_dir,
                          capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _timestamp(entry: Dict[str, Any]) -> str:
    """Sort key for an entry; ISO strings compare correctly as text."""
    value = entry.get('timestamp')
    return value if isinstance(value, str) else ''


def merge_caches(local: Dict[str, Any], remote: Dict[str, Any]):
    """
    Combine two cache dictionaries.

    Returns:
        (merged, gained, contributed) where `gained` counts keys only the remote
        had and `contributed` counts keys only we had.
    """
    merged = dict(remote)
    gained = sum(1 for key in remote if key not in local)
    contributed = 0

    for key, entry in local.items():
        if key not in merged:
            merged[key] = entry
            contributed += 1
        elif _timestamp(entry) > _timestamp(merged[key]):
            merged[key] = entry  # ours is newer, keep it

    return merged, gained, contributed


def _read_json_file(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def _write_cache(path: str, data: Dict[str, Any]) -> None:
    """Write the cache exactly the way CityCache.save_cache does."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def sync_city_cache(logger: Optional[logging.Logger] = None,
                    remote: str = 'origin',
                    repo_dir: str = REPO_DIR,
                    cache_path: str = CACHE_PATH) -> SyncResult:
    """
    Merge the local city cache with the one on the remote, then commit and push.

    The merged cache is always written locally, even when the push cannot go
    through, so nothing that was looked up is lost.
    """
    log = logger or logging.getLogger(__name__)

    try:
        code, branch, err = _git(repo_dir, 'rev-parse', '--abbrev-ref', 'HEAD')
        if code != 0:
            return SyncResult(False, 'This folder is not a git repository', details=err)

        code, _, err = _git(repo_dir, 'fetch', remote, branch)
        if code != 0:
            return SyncResult(False, f'Could not reach {remote}', details=err)

        # The remote copy may not exist yet; that is fine.
        code, remote_text, _ = _git(repo_dir, 'show', f'{remote}/{branch}:{CACHE_REL_PATH}')
        try:
            remote_cache = json.loads(remote_text) if code == 0 and remote_text else {}
        except ValueError:
            remote_cache = {}
        if not isinstance(remote_cache, dict):
            remote_cache = {}

        local_cache = _read_json_file(cache_path)
        merged, gained, contributed = merge_caches(local_cache, remote_cache)
        log.info(f"Cache sync: {len(local_cache)} local, {len(remote_cache)} remote, "
                 f"{len(merged)} merged (+{gained} from remote, +{contributed} from here)")

        # If the branch is behind, fast-forward first. The merged cache is held
        # in memory, so discarding the local file here loses nothing.
        code, behind_count, _ = _git(repo_dir, 'rev-list', '--count', f'HEAD..{remote}/{branch}')
        behind = int(behind_count) if behind_count.isdigit() else 0
        if behind:
            _git(repo_dir, 'checkout', '--', CACHE_REL_PATH)
            code, _, err = _git(repo_dir, 'merge', '--ff-only', f'{remote}/{branch}')
            if code != 0:
                _write_cache(cache_path, merged)
                return SyncResult(
                    False,
                    'The cache was merged locally, but the branch has diverged '
                    'from the remote. Pull manually, then try again.',
                    gained, contributed, details=err)

        _write_cache(cache_path, merged)

        code, _, err = _git(repo_dir, 'add', '--', CACHE_REL_PATH)
        if code != 0:
            return SyncResult(False, 'git add failed', gained, contributed, details=err)

        # Commit only the cache, whatever else may be modified in the tree.
        stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        message = (f"Update city cache from {platform.node()} ({stamp})\n\n"
                   f"{len(merged)} entries after merging "
                   f"({contributed} added here, {gained} taken from the remote).")
        code, out, err = _git(repo_dir, 'commit', '-m', message, '--', CACHE_REL_PATH)
        if code != 0:
            combined = f'{out} {err}'.lower()
            if 'nothing to commit' in combined or 'no changes added' in combined:
                return SyncResult(True, 'Already up to date - nothing to push.',
                                  gained, contributed, pushed=False)
            return SyncResult(False, 'git commit failed', gained, contributed,
                              details=f'{out}\n{err}'.strip())

        code, out, err = _git(repo_dir, 'push', remote, branch)
        if code != 0:
            return SyncResult(False,
                              'The cache was committed locally, but the push failed.',
                              gained, contributed, details=f'{out}\n{err}'.strip())

        return SyncResult(True, 'City cache merged and pushed.',
                          gained, contributed, pushed=True)

    except subprocess.TimeoutExpired:
        return SyncResult(False, 'git took too long and was stopped.')
    except Exception as e:  # pragma: no cover - defensive
        log.error(f"Cache sync failed: {e}")
        return SyncResult(False, f'Unexpected error: {e}')
