"""
EXIF Date Restorer - Core Module

Reverse of the Media File Renamer: instead of building a filename from EXIF
metadata, this reads the capture date/time embedded in a filename and writes it
into the JPEG EXIF metadata - but STRICTLY ONLY for files that do not already
contain EXIF date information (existing dates are never overwritten).

Date format in the filename (always): YYYY.MM.DD
    1999.12.05  ->  5 December 1999

Optional time, right after the date:
    1999.12.05-21.00   (dash separator, HH.MM)
    1999.12.05.21.00   (dot separator, HH.MM)
    1999.12.05         (no time -> 00.00 assumed)
Optional seconds are also accepted (HH.MM.SS), matching the original renamer
output (e.g. 2024.03.14-11.56.10.001.Athens.jpg).

Anything after the date/time part of the name is ignored, so names produced by
the original renamer are parsed correctly.

Three EXIF tags are written (JPEG only):
    DateTimeOriginal   ExifIFD 0x9003
    CreateDate         DateTimeDigitized, ExifIFD 0x9004
    ModifyDate         DateTime, 0th IFD 0x0132
"""

import os
import re
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Callable

import piexif


# Date at the START of the filename, with an optional time component.
# Month/day/time fields accept 1 or 2 digits (e.g. 1999.7.22 == 1999.07.22).
# Separator between date and time can be a dash or a dot.
_DATE_RE = re.compile(
    r'^(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})'
    r'(?:[-.](?P<hour>\d{1,2})\.(?P<minute>\d{1,2})(?:\.(?P<second>\d{1,2}))?)?'
)

# Only JPEG for now (piexif writes JPEG/TIFF reliably; scope is JPEG).
JPEG_EXTENSIONS = {'.jpg', '.jpeg'}

# EXIF datetime format required by the standard: "YYYY:MM:DD HH:MM:SS"
_EXIF_DT_FORMAT = "%Y:%m:%d %H:%M:%S"


class FileStatus(Enum):
    """Outcome of scanning a single file."""
    READY = "ready"          # No EXIF date + parseable filename -> will write
    HAS_EXIF = "has_exif"    # Already has an EXIF date -> skipped (protected)
    NO_DATE = "no_date"      # Filename has no parseable date -> skipped
    ERROR = "error"          # File could not be read/parsed


@dataclass
class ScanResult:
    """Result of examining one candidate file."""
    path: str
    filename: str
    status: FileStatus
    parsed_datetime: Optional[datetime] = None
    message: str = ""


def parse_datetime_from_filename(filename: str) -> Optional[datetime]:
    """
    Parse a capture datetime from the beginning of a filename.

    Args:
        filename: File name or full path. Only the base name is inspected.

    Returns:
        A datetime (missing time defaults to 00:00:00) or None if the name does
        not start with a valid YYYY.MM.DD date.
    """
    name = os.path.basename(filename)
    match = _DATE_RE.match(name)
    if not match:
        return None

    parts = match.groupdict()
    # A month or day of "00" is treated as "01"
    # (e.g. 1999.00.00 -> 1999.01.01, 1999.01.00 -> 1999.01.01).
    month = int(parts['month']) or 1
    day = int(parts['day']) or 1
    try:
        return datetime(
            year=int(parts['year']),
            month=month,
            day=day,
            hour=int(parts['hour']) if parts['hour'] else 0,
            minute=int(parts['minute']) if parts['minute'] else 0,
            second=int(parts['second']) if parts['second'] else 0,
        )
    except ValueError:
        # Out-of-range values (month 13, day 32, hour 25, Feb 30, ...)
        return None


def has_exif_date(filepath: str) -> bool:
    """
    Return True if the JPEG already carries any EXIF date tag.

    Checks DateTimeOriginal, DateTimeDigitized (CreateDate) and DateTime
    (ModifyDate). If any is present the file is considered to "have EXIF
    information" and must not be touched.
    """
    try:
        exif_dict = piexif.load(filepath)
    except Exception:
        # No readable EXIF block at all -> no date present.
        return False

    exif_ifd = exif_dict.get("Exif", {})
    zeroth = exif_dict.get("0th", {})

    return (
        piexif.ExifIFD.DateTimeOriginal in exif_ifd
        or piexif.ExifIFD.DateTimeDigitized in exif_ifd
        or piexif.ImageIFD.DateTime in zeroth
    )


def write_exif_date(filepath: str, dt: datetime) -> None:
    """
    Write ``dt`` into the three EXIF date tags of a JPEG, in place.

    Uses piexif.insert, which rewrites only the EXIF block and leaves the image
    pixel data untouched (non-destructive).

    Raises:
        Exception: propagated if the file cannot be written.
    """
    dt_str = dt.strftime(_EXIF_DT_FORMAT)

    try:
        exif_dict = piexif.load(filepath)
    except Exception:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    exif_dict.setdefault("Exif", {})
    exif_dict.setdefault("0th", {})

    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dt_str
    exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = dt_str   # CreateDate
    exif_dict["0th"][piexif.ImageIFD.DateTime] = dt_str            # ModifyDate

    try:
        exif_bytes = piexif.dump(exif_dict)
    except Exception:
        # A malformed thumbnail / 1st IFD can break dump; drop it and retry.
        exif_dict["1st"] = {}
        exif_dict["thumbnail"] = None
        exif_bytes = piexif.dump(exif_dict)

    piexif.insert(exif_bytes, filepath)


def _scan_file(filepath: str, logger: Optional[logging.Logger] = None) -> ScanResult:
    """Examine a single file and classify what should happen to it."""
    fname = os.path.basename(filepath)
    dt = parse_datetime_from_filename(fname)

    if dt is None:
        return ScanResult(filepath, fname, FileStatus.NO_DATE,
                          message="No YYYY.MM.DD date in filename")

    try:
        if has_exif_date(filepath):
            return ScanResult(filepath, fname, FileStatus.HAS_EXIF, dt,
                              "Already has EXIF date - skipped")
    except Exception as e:  # pragma: no cover - defensive
        if logger:
            logger.error(f"Error reading EXIF from {filepath}: {e}")
        return ScanResult(filepath, fname, FileStatus.ERROR, dt, f"Read error: {e}")

    return ScanResult(filepath, fname, FileStatus.READY, dt,
                      f"Will set {dt.strftime(_EXIF_DT_FORMAT)}")


def scan_folder(folder: str, recursive: bool = True,
                logger: Optional[logging.Logger] = None) -> List[ScanResult]:
    """
    Scan a folder for JPEG files and classify each one.

    Args:
        folder: Root folder to scan.
        recursive: If True, descend into all sub-folders (and their sub-folders).
        logger: Optional logger.

    Returns:
        List of ScanResult, one per JPEG found.
    """
    results: List[ScanResult] = []

    for root, _dirs, files in os.walk(folder):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in JPEG_EXTENSIONS:
                continue
            results.append(_scan_file(os.path.join(root, fname), logger))
        if not recursive:
            break

    if logger:
        logger.info(f"Scanned {folder} (recursive={recursive}): {len(results)} JPEG files")
    return results


def apply_dates(results: List[ScanResult],
                logger: Optional[logging.Logger] = None,
                progress: Optional[Callable[[int, int, ScanResult], None]] = None):
    """
    Write EXIF dates for every ScanResult whose status is READY.

    Args:
        results: The scan results to act on. Non-READY entries are ignored.
        logger: Optional logger.
        progress: Optional callback(index, total, result) called per READY item.

    Returns:
        Tuple (written_count, error_count).
    """
    ready = [r for r in results if r.status == FileStatus.READY]
    total = len(ready)
    written = 0
    errors = 0

    for i, r in enumerate(ready, start=1):
        try:
            write_exif_date(r.path, r.parsed_datetime)
            written += 1
            if logger:
                logger.info(f"Wrote EXIF date {r.parsed_datetime} -> {r.filename}")
        except Exception as e:
            errors += 1
            r.status = FileStatus.ERROR
            r.message = f"Write error: {e}"
            if logger:
                logger.error(f"Failed to write EXIF to {r.path}: {e}")
        if progress:
            progress(i, total, r)

    if logger:
        logger.info(f"Apply finished: {written} written, {errors} errors")
    return written, errors
