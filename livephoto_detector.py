"""
Live Photo detector and organiser.

An iPhone Live Photo is a still image plus a short .mov clip. The clip is tagged
with a QuickTime metadata key - ``com.apple.quicktime.content.identifier`` - that
pairs it with its still. This is exactly what ``exiftool -ContentIdentifier``
reports; here we read it straight from the MOV's ``moov`` atom, so no external
tool is required.

The organiser moves the detected clips into a ``livephoto`` sub-folder created
inside each clip's own folder (per-folder layout), never overwriting anything.
"""

import os
import struct
import shutil
import logging
from typing import Optional, List, Tuple, Callable

# The QuickTime metadata key that marks a Live Photo clip (== exiftool's
# "ContentIdentifier" tag).
_CONTENT_ID_KEY = b'com.apple.quicktime.content.identifier'

# Name of the sub-folder the clips are moved into.
LIVEPHOTO_DIR = 'livephoto'

MOV_EXTENSIONS = {'.mov'}


def _next_atom(f, pos: int):
    """Read one atom header at pos. Returns (type_bytes, header_size, size)."""
    f.seek(pos)
    header = f.read(8)
    if len(header) < 8:
        return None, 0, 0
    size = struct.unpack('>I', header[:4])[0]
    atom_type = header[4:8]
    header_size = 8
    if size == 1:  # 64-bit extended size
        size = struct.unpack('>Q', f.read(8))[0]
        header_size = 16
    return atom_type, header_size, size


def _find_child_bytes(f, start: int, end: int, target: bytes) -> Optional[bytes]:
    """Return the raw bytes of the first direct child atom of the given type."""
    pos = start
    while pos < end:
        atom_type, header_size, size = _next_atom(f, pos)
        if atom_type is None:
            break
        if size == 0:
            size = end - pos
        if size < header_size:
            break  # malformed; stop
        if atom_type == target:
            f.seek(pos + header_size)
            return f.read(size - header_size)
        pos += size
    return None


def _find_moov(f) -> Tuple[Optional[int], Optional[int]]:
    """Return (content_start, content_end) of the moov atom, or (None, None)."""
    f.seek(0, os.SEEK_END)
    end = f.tell()
    pos = 0
    while pos < end:
        atom_type, header_size, size = _next_atom(f, pos)
        if atom_type is None:
            break
        if size == 0:
            size = end - pos
        if size < header_size:
            break
        if atom_type == b'moov':
            return pos + header_size, pos + size
        pos += size
    return None, None


def is_live_photo(filepath: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    Return True if the .mov carries a Live Photo content identifier.

    Reads only the small metadata atoms (moov/meta, or moov/udta/meta) - the
    media payload is never read.
    """
    try:
        with open(filepath, 'rb') as f:
            moov_start, moov_end = _find_moov(f)
            if moov_start is None:
                return False

            # The identifier lives in moov/meta (iPhone) or moov/udta/meta.
            meta = _find_child_bytes(f, moov_start, moov_end, b'meta')
            if meta is not None and _CONTENT_ID_KEY in meta:
                return True

            udta = _find_child_bytes(f, moov_start, moov_end, b'udta')
            if udta is not None and _CONTENT_ID_KEY in udta:
                return True
        return False
    except Exception as e:
        if logger:
            logger.error(f"Error reading Live Photo metadata from {filepath}: {e}")
        return False


def scan_live_photos(folder: str, recursive: bool = True,
                     logger: Optional[logging.Logger] = None) -> List[str]:
    """
    Find every Live Photo .mov under ``folder``.

    Files already inside a ``livephoto`` sub-folder are skipped, so re-running is
    safe.

    Returns:
        List of absolute paths to Live Photo clips.
    """
    found: List[str] = []
    for root, dirs, files in os.walk(folder):
        # Do not descend into (or collect from) existing livephoto folders.
        dirs[:] = [d for d in dirs if d.lower() != LIVEPHOTO_DIR]
        if os.path.basename(root).lower() == LIVEPHOTO_DIR:
            continue
        for fname in files:
            if os.path.splitext(fname)[1].lower() in MOV_EXTENSIONS:
                path = os.path.join(root, fname)
                if is_live_photo(path, logger):
                    found.append(path)
        if not recursive:
            break

    if logger:
        logger.info(f"Live Photo scan of {folder} (recursive={recursive}): "
                    f"{len(found)} clip(s)")
    return found


def _unique_destination(dst: str, reserved: set) -> str:
    """Return a path that clashes with neither an existing file nor a plan."""
    if dst.lower() not in reserved and not os.path.exists(dst):
        return dst
    stem, ext = os.path.splitext(dst)
    i = 1
    while True:
        candidate = f"{stem} ({i}){ext}"
        if candidate.lower() not in reserved and not os.path.exists(candidate):
            return candidate
        i += 1


def plan_moves(paths: List[str]) -> List[Tuple[str, str]]:
    """
    Build (source, destination) pairs, one per clip.

    Each destination is a ``livephoto`` folder inside the clip's own directory,
    with a collision-safe filename.
    """
    plans: List[Tuple[str, str]] = []
    reserved: set = set()
    for src in paths:
        target_dir = os.path.join(os.path.dirname(src), LIVEPHOTO_DIR)
        dst = _unique_destination(
            os.path.join(target_dir, os.path.basename(src)), reserved)
        reserved.add(dst.lower())
        plans.append((src, dst))
    return plans


def move_live_photos(paths: List[str],
                     logger: Optional[logging.Logger] = None,
                     progress: Optional[Callable[[int, int, str], None]] = None
                     ) -> Tuple[int, int, List[Tuple[str, Optional[str], Optional[str]]]]:
    """
    Move each clip into a per-folder ``livephoto`` sub-folder.

    Returns:
        (moved_count, error_count, results) where each result is
        (source, destination_or_None, error_or_None).
    """
    plans = plan_moves(paths)
    total = len(plans)
    moved = 0
    errors = 0
    results: List[Tuple[str, Optional[str], Optional[str]]] = []

    for i, (src, dst) in enumerate(plans, start=1):
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            moved += 1
            results.append((src, dst, None))
            if logger:
                logger.info(f"Moved Live Photo {os.path.basename(src)} -> {dst}")
        except Exception as e:
            errors += 1
            results.append((src, None, str(e)))
            if logger:
                logger.error(f"Failed to move {src}: {e}")
        if progress:
            progress(i, total, src)

    if logger:
        logger.info(f"Live Photo move finished: {moved} moved, {errors} errors")
    return moved, errors, results
