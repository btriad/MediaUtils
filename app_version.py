"""
Version label shown in the top-right corner of both applications.

The date part is the date of the last commit, so the label says which build of
the code is running - useful when the same project is used on more than one
machine. When git is not available (a copy without the .git folder, for
example), the newest source file's modification date is used instead.
"""

import os
import subprocess
from datetime import datetime

VERSION = '2.0.0'

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)  # no console flash on Windows

_cached_label = None


def build_date() -> str:
    """Date of the last commit as YYYY.MM.DD, or of the newest source file."""
    try:
        proc = subprocess.run(
            ['git', 'log', '-1', '--format=%cd', '--date=format:%Y.%m.%d'],
            cwd=_PROJECT_DIR, capture_output=True, text=True,
            timeout=10, creationflags=_NO_WINDOW)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, ValueError, subprocess.SubprocessError):
        pass  # no git, not a repository, or it took too long

    newest = 0.0
    for name in os.listdir(_PROJECT_DIR):
        if name.endswith('.py'):
            try:
                newest = max(newest, os.path.getmtime(os.path.join(_PROJECT_DIR, name)))
            except OSError:
                continue

    stamp = datetime.fromtimestamp(newest) if newest else datetime.now()
    return stamp.strftime('%Y.%m.%d')


def version_label() -> str:
    """The label for the corner, e.g. 'v2.0.0.2026.09.12'. Computed once."""
    global _cached_label
    if _cached_label is None:
        _cached_label = f'v{VERSION}.{build_date()}'
    return _cached_label
