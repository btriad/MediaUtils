"""
Video Date Restorer - in-place creation_time editing for MP4/MOV/M4V.

QuickTime / ISO Base Media File Format containers (MP4, MOV, M4V, 3GP) store the
recording date as a fixed-size field - seconds since 1904-01-01 UTC - inside the
``mvhd``, ``tkhd`` and ``mdhd`` header atoms. Because the field is fixed size we
can overwrite exactly those bytes in place, without rebuilding the file. The
media payload (``mdat``) is never touched: no remux, no re-encode, no quality
loss, and the file size is unchanged - exactly like editing EXIF in a JPEG.

Only these containers are editable this way. Other video formats (MKV, AVI, WMV,
FLV, WebM) use entirely different structures and would require a full remux, so
they are intentionally not handled here.
"""

import os
import struct
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

# Containers we can edit in place (ISO-BMFF / QuickTime family).
BMFF_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.m4v', '.3gp'}

# Recognised video formats that CANNOT be edited in place (need a remux).
NON_BMFF_VIDEO_EXTENSIONS = {'.mkv', '.avi', '.wmv', '.flv', '.webm'}

# The QuickTime/MP4 epoch: seconds are counted from 1904-01-01 00:00:00 UTC.
_EPOCH_1904 = datetime(1904, 1, 1)

# Atoms that contain child atoms we need to descend into.
_CONTAINER_ATOMS = {b'moov', b'trak', b'mdia'}
# Header atoms that carry a creation_time / modification_time pair.
_TIME_ATOMS = {b'mvhd', b'tkhd', b'mdhd'}

# Largest value the 32-bit (version 0) field can hold (~year 2040).
_UINT32_MAX = 0xFFFFFFFF


def _seconds_since_1904(dt: datetime) -> int:
    """Convert a datetime to seconds since the QuickTime epoch (1904-01-01)."""
    return int((dt - _EPOCH_1904).total_seconds())


def _iter_time_atoms(f, start: int, end: int) -> List[Tuple[int, int]]:
    """
    Walk the atom tree and collect every mvhd/tkhd/mdhd time field.

    Only container atoms (moov/trak/mdia) are descended into, so the large
    ``mdat`` payload is skipped by seeking past it - nothing there is read.

    Returns:
        List of (creation_time_offset, version) tuples. The offset points at the
        creation_time field; modification_time immediately follows it.
    """
    found: List[Tuple[int, int]] = []
    pos = start
    while pos < end:
        f.seek(pos)
        header = f.read(8)
        if len(header) < 8:
            break
        size = struct.unpack('>I', header[:4])[0]
        atom_type = header[4:8]
        header_size = 8
        if size == 1:  # 64-bit extended size
            size = struct.unpack('>Q', f.read(8))[0]
            header_size = 16
        elif size == 0:  # extends to end of file
            size = end - pos
        if size < header_size:
            break  # malformed; stop to avoid an infinite loop

        if atom_type in _CONTAINER_ATOMS:
            found.extend(_iter_time_atoms(f, pos + header_size, pos + size))
        elif atom_type in _TIME_ATOMS:
            f.seek(pos + header_size)
            version = f.read(1)[0]
            # Layout: version(1) + flags(3) + creation_time + modification_time
            found.append((pos + header_size + 4, version))

        pos += size
    return found


def has_video_date(filepath: str, logger: Optional[logging.Logger] = None) -> bool:
    """
    Return True if the video already has a creation date in its mvhd atom.

    A creation_time of 0 means "unset", so such files are treated as having no
    date (and are therefore candidates for writing).
    """
    try:
        with open(filepath, 'rb') as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            for offset, version in _iter_time_atoms(f, 0, end):
                f.seek(offset)
                if version == 1:
                    value = struct.unpack('>Q', f.read(8))[0]
                else:
                    value = struct.unpack('>I', f.read(4))[0]
                if value != 0:
                    return True  # mvhd is listed first; any non-zero = has date
        return False
    except Exception as e:
        if logger:
            logger.error(f"Error reading video date from {filepath}: {e}")
        # Unreadable structure -> don't claim it has a date, but writing will
        # also fail and be reported there.
        return False


def write_video_date(filepath: str, dt: datetime,
                     logger: Optional[logging.Logger] = None) -> None:
    """
    Write ``dt`` into the mvhd/tkhd/mdhd creation & modification time fields,
    in place. The media streams and file size are left untouched.

    Raises:
        ValueError: if the date is out of the representable range or no editable
            header atom is found.
        Exception: propagated on I/O errors.
    """
    secs = _seconds_since_1904(dt)
    if secs < 0:
        raise ValueError(f"Date {dt} is before 1904 and cannot be stored")

    with open(filepath, 'r+b') as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        fields = _iter_time_atoms(f, 0, end)
        if not fields:
            raise ValueError("No mvhd/tkhd/mdhd atom found (not an MP4/MOV?)")

        for offset, version in fields:
            if version == 1:
                packed = struct.pack('>Q', secs)          # 8 bytes each
            else:
                if secs > _UINT32_MAX:
                    raise ValueError(
                        f"Date {dt} exceeds the 32-bit field limit (~2040)")
                packed = struct.pack('>I', secs)          # 4 bytes each
            f.seek(offset)
            f.write(packed)          # creation_time
            f.write(packed)          # modification_time (immediately follows)

    if logger:
        logger.info(f"Patched creation_time in place -> {os.path.basename(filepath)}")
