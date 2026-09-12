"""
Media Processing Module

Handles extraction of metadata from images and videos including:
- Date/time information from EXIF data
- GPS coordinates and location data
- File format detection and validation
- City caching for GPS coordinates
- Error recovery with retry logic
"""

import os
import json
import subprocess
import time
import threading
import logging
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
from PIL import Image
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener
import urllib.request
import urllib.parse
import urllib.error
import re
import unicodedata
from city_cache import CityCache
from error_recovery import ErrorRecovery
from xmp_handler import XMPHandler

# Try to import exifread for better RAW file support
try:
    import exifread
    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False
    print("Note: exifread not available. RAW file metadata extraction may be limited.")
    print("Install with: pip install exifread")


class _NominatimRateLimiter:
    """
    Process-wide throttle for the OpenStreetMap Nominatim API.

    Nominatim's usage policy allows at most one request per second, so requests
    are spaced MIN_INTERVAL apart. After an HTTP 429 the next request is held
    back 30s (60s if it happens again, or the server's Retry-After). If the
    server keeps refusing, lookups pause for BLOCK_SECONDS so a scan is not
    stalled indefinitely - affected files get no city (it is not cached) and
    are retried on the next run.
    """
    MIN_INTERVAL = 1.1      # seconds between requests (policy: max 1/s)
    FIRST_429_WAIT = 30     # back-off after the first 429
    REPEAT_429_WAIT = 60    # back-off after further consecutive 429s
    MAX_RETRY_AFTER = 120   # cap for a server-supplied Retry-After
    TRIP_AFTER = 3          # consecutive 429s before pausing lookups
    BLOCK_SECONDS = 300     # how long lookups stay paused once tripped

    def __init__(self):
        self._lock = threading.Lock()
        self._next_allowed = 0.0
        self._consecutive_429 = 0
        self._blocked_until = 0.0

    def is_blocked(self) -> bool:
        return time.monotonic() < self._blocked_until

    def wait_turn(self, wait_callback=None) -> None:
        """Block until the caller may send its request (reserves the slot)."""
        with self._lock:
            start = max(time.monotonic(), self._next_allowed)
            self._next_allowed = start + self.MIN_INTERVAL
        while True:
            remaining = start - time.monotonic()
            if remaining <= 0:
                return
            if wait_callback:
                wait_callback(remaining)
            time.sleep(min(0.1, remaining))

    def note_success(self) -> None:
        with self._lock:
            self._consecutive_429 = 0

    def note_rate_limited(self, retry_after: Optional[int] = None) -> int:
        """Record an HTTP 429; return how many seconds lookups are held back."""
        with self._lock:
            self._consecutive_429 += 1
            if self._consecutive_429 >= self.TRIP_AFTER:
                self._consecutive_429 = 0
                self._blocked_until = time.monotonic() + self.BLOCK_SECONDS
                return self.BLOCK_SECONDS
            if retry_after is not None and retry_after > 0:
                wait = min(retry_after, self.MAX_RETRY_AFTER)
            elif self._consecutive_429 == 1:
                wait = self.FIRST_429_WAIT
            else:
                wait = self.REPEAT_429_WAIT
            self._next_allowed = max(self._next_allowed, time.monotonic() + wait)
            return wait


# Shared by every MediaProcessor: the limit applies per client, not per object.
_nominatim_limiter = _NominatimRateLimiter()


# --- Latin transliteration ---------------------------------------------------
# City names end up inside filenames, so they must stay portable. Nominatim is
# asked for English names, but it falls back to the local name when no English
# one exists (e.g. "Δημοτική Ενότητα Φραγκίστας", "Beşiktaş", or a Chinese name).

_GREEK_MAP = {
    'α': 'a', 'β': 'v', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'i',
    'θ': 'th', 'ι': 'i', 'κ': 'k', 'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x',
    'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's', 'ς': 's', 'τ': 't', 'υ': 'y',
    'φ': 'f', 'χ': 'ch', 'ψ': 'ps', 'ω': 'o',
}

# Latin letters that survive diacritic stripping and need an explicit mapping.
_LATIN_EXTRAS = {
    'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S',
    'ø': 'o', 'Ø': 'O', 'æ': 'ae', 'Æ': 'AE', 'œ': 'oe', 'Œ': 'OE',
    'ß': 'ss', 'đ': 'd', 'Đ': 'D', 'ł': 'l', 'Ł': 'L',
    'þ': 'th', 'Þ': 'Th', 'ð': 'd', 'Ð': 'D',
}

try:  # optional: adds Cyrillic, Chinese (pinyin), Japanese, Arabic, ...
    from unidecode import unidecode as _unidecode
except ImportError:
    _unidecode = None


def to_latin(text: str) -> str:
    """
    Render a place name in Latin letters so it is safe inside a filename.

    Greek uses a dedicated table (Φραγκίστα -> Fragkista); Turkish and accented
    Latin letters are folded to ASCII (Beşiktaş -> Besiktas). Other scripts are
    handled by the optional `unidecode` package; without it a name that cannot
    be converted is returned unchanged rather than lost.
    """
    if not text or text.isascii():
        return text

    # Drop diacritics first: é -> e, ö -> o, ά -> α, ş -> s, ğ -> g
    stripped = ''.join(c for c in unicodedata.normalize('NFD', text)
                       if not unicodedata.combining(c))

    out = []
    i = 0
    while i < len(stripped):
        ch = stripped[i]
        if stripped[i:i + 2].lower() == 'ου':  # Σχηματαρίου -> Schimatariou
            nxt = stripped[i + 1]
            out.append('OU' if ch.isupper() and nxt.isupper()
                       else 'Ou' if ch.isupper() else 'ou')
            i += 2
            continue
        lowered = ch.lower()
        if lowered in _GREEK_MAP:
            latin = _GREEK_MAP[lowered]
            out.append(latin.capitalize() if ch.isupper() else latin)
        elif ch in _LATIN_EXTRAS:
            out.append(_LATIN_EXTRAS[ch])
        else:
            out.append(ch)
        i += 1

    result = ''.join(out)
    if not result.isascii() and _unidecode is not None:
        result = _unidecode(result)
    return result.strip() or text


class MediaProcessor:
    """Handles metadata extraction and processing for media files with caching and error recovery."""
    
    def __init__(self, city_cache: Optional[CityCache] = None, logger: Optional[logging.Logger] = None, error_recovery: Optional[ErrorRecovery] = None):
        """
        Initialize the media processor with supported file extensions.
        
        Args:
            city_cache: Optional city cache instance for GPS lookups
            logger: Optional logger instance for error tracking
            error_recovery: Optional error recovery system instance
        """
        # Register HEIF opener for Pillow to handle HEIC/HEIF files
        register_heif_opener()
        
        # Initialize XMP handler for sidecar file support
        self.xmp_handler = XMPHandler(logger=logger)
        
        # Supported file extensions
        self.image_extensions = {
            # Standard formats
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', 
            '.tiff', '.webp', '.heic', '.heif',
            # RAW formats
            '.nef',   # Nikon RAW
            '.cr2', '.cr3',  # Canon RAW
            '.arw',   # Sony RAW
            '.dng',   # Adobe Digital Negative
            '.orf',   # Olympus RAW
            '.rw2',   # Panasonic RAW
            '.pef',   # Pentax RAW
            '.raf'    # Fujifilm RAW
        }
        self.video_extensions = {
            '.mp4', '.avi', '.mov', '.mkv', '.wmv', 
            '.flv', '.webm'
        }
        
        # Initialize caching and logging
        self.city_cache = city_cache or CityCache()
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize error recovery system
        self.error_recovery = error_recovery or ErrorRecovery(logger=self.logger, max_retries=3)
        
        # Network retry configuration
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay for exponential backoff
        self.network_timeout = 10  # Timeout for network requests
        # Optional callable(remaining_seconds), invoked while a city lookup waits
        # on the OpenStreetMap rate limit so a GUI can show a countdown.
        self.network_wait_callback = None
        
        # Log initialization
        self.logger.info("MediaProcessor initialized with caching and error recovery")
    
    def is_supported_file(self, filepath: str) -> bool:
        """Check if file is a supported media type."""
        ext = os.path.splitext(filepath.lower())[1]
        return ext in self.image_extensions or ext in self.video_extensions
    
    def get_file_date(self, filepath: str) -> Tuple[Optional[datetime], bool]:
        """
        Extract creation date from media file metadata.
        
        Args:
            filepath: Path to the media file
            
        Returns:
            Tuple of (datetime object, has_metadata_flag)
        """
        self.logger.debug(f"Extracting date from {filepath}")
        
        try:
            ext = os.path.splitext(filepath.lower())[1]
            
            # Process image files
            if ext in self.image_extensions:
                result = self._extract_image_date(filepath)
                if result[0]:
                    self.logger.info(f"Successfully extracted date from image {filepath}: {result[0]}")
                    return result
                else:
                    self.logger.debug(f"No date metadata found in image {filepath}, checking XMP")
                    # Check XMP sidecar file for date
                    xmp_file = self.xmp_handler.find_xmp_file(filepath)
                    if xmp_file:
                        xmp_date = self.xmp_handler.extract_date_from_xmp(xmp_file)
                        if xmp_date:
                            self.logger.info(f"Using date from XMP sidecar: {xmp_date}")
                            return xmp_date, True
                    return result
            
            # Process video files
            elif ext in self.video_extensions:
                result = self._extract_video_date(filepath)
                if result[0]:
                    self.logger.info(f"Successfully extracted date from video {filepath}: {result[0]}")
                else:
                    self.logger.debug(f"No date metadata found in video {filepath}")
                return result
            
            self.logger.warning(f"Unsupported file type for {filepath}")
            return None, False
            
        except Exception as e:
            self.logger.error(f"Error extracting date from {filepath}: {e}")
            print(f"Error extracting date from {filepath}: {e}")
            return None, False
    
    def _extract_image_date(self, filepath: str) -> Tuple[Optional[datetime], bool]:
        """Extract date from image EXIF data with error recovery and RAW file support."""
        ext = os.path.splitext(filepath.lower())[1]
        
        # For RAW files, try exifread first if available
        if ext in {'.nef', '.cr2', '.cr3', '.arw', '.dng', '.orf', '.rw2', '.pef', '.raf'}:
            if EXIFREAD_AVAILABLE:
                result = self._extract_date_with_exifread(filepath)
                if result[0]:
                    return result
                # If exifread fails, fall through to PIL method
        
        # Try PIL/Pillow for standard formats and as fallback for RAW
        try:
            with Image.open(filepath) as img:
                exif = img.getexif()
                if not exif:
                    self.logger.debug(f"No EXIF data found in {filepath}")
                    return None, False
                
                # Try different date fields in order of preference
                date_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
                
                for field in date_fields:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag == field:
                            try:
                                parsed_date = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                                self.logger.debug(f"Extracted date from {filepath}: {parsed_date}")
                                return parsed_date, True
                            except ValueError as e:
                                self.logger.warning(f"Invalid date format in {filepath} for field {field}: {value}")
                                continue
                
                self.logger.debug(f"No valid date fields found in {filepath}")
                return None, False
                
        except (IOError, OSError, PermissionError) as e:
            # Handle file permission errors using error recovery
            recovery_result = self.error_recovery.handle_file_permission_error(filepath, "read")
            return None, False
        except Exception as e:
            # Handle corrupted file errors using error recovery
            recovery_result = self.error_recovery.handle_corrupted_file_error(filepath, e)
            return None, False
    
    def _extract_date_with_exifread(self, filepath: str) -> Tuple[Optional[datetime], bool]:
        """Extract date from RAW files using exifread library."""
        try:
            with open(filepath, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                
                # Try different date fields in order of preference
                date_fields = [
                    'EXIF DateTimeOriginal',
                    'EXIF DateTimeDigitized', 
                    'Image DateTime'
                ]
                
                for field in date_fields:
                    if field in tags:
                        try:
                            date_str = str(tags[field])
                            parsed_date = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                            self.logger.debug(f"Extracted date from RAW file {filepath}: {parsed_date}")
                            return parsed_date, True
                        except ValueError as e:
                            self.logger.warning(f"Invalid date format in {filepath} for field {field}: {date_str}")
                            continue
                
                self.logger.debug(f"No valid date fields found in RAW file {filepath}")
                return None, False
                
        except Exception as e:
            self.logger.warning(f"Failed to extract date from RAW file {filepath}: {e}")
            return None, False
    
    def _extract_video_date(self, filepath: str) -> Tuple[Optional[datetime], bool]:
        """Extract date from video metadata using ffprobe with error recovery."""
        # Check if ffprobe is available using error recovery system
        ffprobe_check = self.error_recovery.handle_ffprobe_unavailable(filepath)
        if not ffprobe_check.success:
            # ffprobe not available, continue with image-only processing
            return None, False
        
        # Try local ffprobe.exe first, then system PATH
        ffprobe_paths = [
            os.path.join(os.path.dirname(__file__), 'ffprobe.exe'),  # Local
            'ffprobe'  # System PATH
        ]
        
        for ffprobe_path in ffprobe_paths:
            try:
                # Try different metadata fields that contain creation time
                for field in ['creation_time', 'date']:
                    result = subprocess.run([
                        ffprobe_path, '-v', 'quiet', 
                        '-show_entries', f'format_tags={field}',
                        '-of', 'csv=p=0', filepath
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        date_str = result.stdout.strip()
                        
                        # Try different datetime formats
                        formats = ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ']
                        for fmt in formats:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                self.logger.debug(f"Extracted video date from {filepath}: {parsed_date}")
                                return parsed_date, True
                            except ValueError:
                                continue
                
                break  # If ffprobe worked, don't try other paths
                
            except subprocess.TimeoutExpired:
                self.logger.warning(f"ffprobe timeout for {filepath}")
                continue
            except FileNotFoundError:
                continue  # Try next ffprobe path
            except Exception as e:
                # Use error recovery to handle unexpected errors
                recovery_result = self.error_recovery.log_and_continue(e, "ffprobe execution", filepath)
                continue
        
        self.logger.debug(f"No date metadata found in video {filepath}")
        return None, False
    
    def get_location_and_city(self, filepath: str) -> Tuple[str, str]:
        """
        Extract GPS coordinates and convert to city name with caching.
        
        Args:
            filepath: Path to the media file
            
        Returns:
            Tuple of (location_string, city_name)
        """
        self.logger.debug(f"Extracting GPS location from {filepath}")
        
        try:
            ext = os.path.splitext(filepath.lower())[1]
            
            # Process image GPS data
            if ext in self.image_extensions:
                lat, lon = self._extract_image_gps(filepath)
                
                # If no GPS in image, check XMP sidecar file
                if (lat is None or lon is None):
                    xmp_file = self.xmp_handler.find_xmp_file(filepath)
                    if xmp_file:
                        self.logger.debug(f"Checking XMP sidecar for GPS: {os.path.basename(xmp_file)}")
                        xmp_lat, xmp_lon = self.xmp_handler.extract_gps_from_xmp(xmp_file)
                        if xmp_lat is not None and xmp_lon is not None:
                            lat, lon = xmp_lat, xmp_lon
                            self.logger.info(f"Using GPS from XMP sidecar: {lat:.6f}, {lon:.6f}")
            
            # Process video GPS data
            elif ext in self.video_extensions:
                lat, lon = self._extract_video_gps(filepath)
            
            else:
                self.logger.debug(f"Unsupported file type for GPS extraction: {filepath}")
                return "No GPS", ""
            
            # Convert coordinates to city name
            if lat is not None and lon is not None:
                location = f"{lat:.4f}, {lon:.4f}"
                self.logger.info(f"GPS coordinates found in {filepath}: {location}")
                city = self._get_city_from_coords_cached(lat, lon)
                if city:
                    self.logger.info(f"City resolved for {filepath}: {city}")
                else:
                    self.logger.warning(f"Could not resolve city for coordinates {location} from {filepath}")
                return location, city
            
            self.logger.debug(f"No GPS coordinates found in {filepath}")
            return "No GPS", ""
            
        except Exception as e:
            self.logger.error(f"Error extracting location from {filepath}: {e}")
            print(f"Error extracting location from {filepath}: {e}")
            return "No GPS", ""
    
    def _extract_image_gps(self, filepath: str) -> Tuple[Optional[float], Optional[float]]:
        """Extract GPS coordinates from image EXIF data with error recovery and RAW file support."""
        ext = os.path.splitext(filepath.lower())[1]
        
        # For RAW files, try exifread first if available
        if ext in {'.nef', '.cr2', '.cr3', '.arw', '.dng', '.orf', '.rw2', '.pef', '.raf'}:
            if EXIFREAD_AVAILABLE:
                self.logger.debug(f"Attempting GPS extraction from RAW file using exifread: {filepath}")
                result = self._extract_gps_with_exifread(filepath)
                if result[0] is not None and result[1] is not None:
                    self.logger.info(f"GPS extracted from RAW file: {filepath} -> {result}")
                    return result
                else:
                    self.logger.debug(f"exifread GPS extraction returned None, trying PIL fallback")
                # If exifread fails, fall through to PIL method
            else:
                self.logger.warning(f"exifread not available for RAW file GPS extraction: {filepath}")
                self.logger.warning("Install exifread for better RAW support: pip install exifread")
        
        # Try PIL/Pillow for standard formats and as fallback for RAW
        try:
            with Image.open(filepath) as img:
                exif = img.getexif()
                if not exif:
                    return None, None
                
                # Try to get GPS IFD (Image File Directory)
                gps_info = None
                try:
                    gps_info = exif.get_ifd(0x8825)  # GPS IFD tag
                except:
                    # Fallback: check if GPS data is directly in EXIF
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag == 'GPSInfo':
                            gps_info = value
                            break
                
                if gps_info and isinstance(gps_info, dict):
                    lat = self._get_gps_coordinate(gps_info, 2, 1)  # Latitude
                    lon = self._get_gps_coordinate(gps_info, 4, 3)  # Longitude
                    if lat is not None and lon is not None:
                        self.logger.debug(f"Extracted GPS from {filepath}: {lat}, {lon}")
                    return lat, lon
                
                return None, None
                
        except (IOError, OSError, PermissionError) as e:
            # Handle file permission errors using error recovery
            recovery_result = self.error_recovery.handle_file_permission_error(filepath, "read")
            return None, None
        except Exception as e:
            # Handle corrupted file errors using error recovery
            recovery_result = self.error_recovery.handle_corrupted_file_error(filepath, e)
            return None, None
    
    def _extract_gps_with_exifread(self, filepath: str) -> Tuple[Optional[float], Optional[float]]:
        """Extract GPS coordinates from RAW files using exifread library."""
        try:
            with open(filepath, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                
                self.logger.debug(f"exifread found {len(tags)} total tags in {os.path.basename(filepath)}")
                
                # Check for GPS tags
                gps_lat = tags.get('GPS GPSLatitude')
                gps_lat_ref = tags.get('GPS GPSLatitudeRef')
                gps_lon = tags.get('GPS GPSLongitude')
                gps_lon_ref = tags.get('GPS GPSLongitudeRef')
                
                # Log GPS tag availability
                gps_tags_found = []
                if gps_lat: gps_tags_found.append('Latitude')
                if gps_lat_ref: gps_tags_found.append('LatitudeRef')
                if gps_lon: gps_tags_found.append('Longitude')
                if gps_lon_ref: gps_tags_found.append('LongitudeRef')
                
                if gps_tags_found:
                    self.logger.debug(f"GPS tags found: {', '.join(gps_tags_found)}")
                else:
                    self.logger.debug(f"No GPS tags found in {os.path.basename(filepath)}")
                    # List all GPS-related tags for debugging
                    gps_related = [k for k in tags.keys() if 'GPS' in k]
                    if gps_related:
                        self.logger.debug(f"GPS-related tags present: {gps_related}")
                    return None, None
                
                if gps_lat and gps_lon and gps_lat_ref and gps_lon_ref:
                    self.logger.debug(f"Converting GPS coordinates: Lat={gps_lat} {gps_lat_ref}, Lon={gps_lon} {gps_lon_ref}")
                    
                    # Convert GPS coordinates to decimal degrees
                    lat = self._convert_gps_to_decimal(gps_lat.values, str(gps_lat_ref))
                    lon = self._convert_gps_to_decimal(gps_lon.values, str(gps_lon_ref))
                    
                    if lat is not None and lon is not None:
                        self.logger.info(f"Successfully extracted GPS from RAW file {os.path.basename(filepath)}: {lat:.6f}, {lon:.6f}")
                        return lat, lon
                    else:
                        self.logger.warning(f"GPS coordinate conversion failed for {os.path.basename(filepath)}")
                else:
                    self.logger.debug(f"Incomplete GPS data in {os.path.basename(filepath)}")
                
                return None, None
                
        except Exception as e:
            self.logger.error(f"Failed to extract GPS from RAW file {filepath}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None, None
    
    def _convert_gps_to_decimal(self, gps_values, ref: str) -> Optional[float]:
        """Convert GPS coordinates from degrees/minutes/seconds to decimal degrees."""
        try:
            # GPS values are typically [degrees, minutes, seconds]
            degrees = float(gps_values[0].num) / float(gps_values[0].den)
            minutes = float(gps_values[1].num) / float(gps_values[1].den)
            seconds = float(gps_values[2].num) / float(gps_values[2].den)
            
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            
            # Apply reference (N/S for latitude, E/W for longitude)
            if ref in ['S', 'W']:
                decimal = -decimal
            
            return decimal
        except Exception as e:
            self.logger.warning(f"Failed to convert GPS coordinates: {e}")
            return None
    
    def _extract_video_gps(self, filepath: str) -> Tuple[Optional[float], Optional[float]]:
        """Extract GPS coordinates from video metadata with error recovery."""
        ffprobe_paths = [
            os.path.join(os.path.dirname(__file__), 'ffprobe.exe'),
            'ffprobe'
        ]
        
        for ffprobe_path in ffprobe_paths:
            try:
                # Get format tags which may contain GPS data
                result = subprocess.run([
                    ffprobe_path, '-v', 'quiet', '-show_entries', 'format_tags',
                    '-of', 'csv=p=0', filepath
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    
                    # Look for GPS pattern like +38.0150+023.8204+214.199005/
                    gps_match = re.search(r'([+-]\d+\.\d+)([+-]\d+\.\d+)', output)
                    if gps_match:
                        lat = float(gps_match.group(1))
                        lon = float(gps_match.group(2))
                        self.logger.debug(f"Extracted video GPS from {filepath}: {lat}, {lon}")
                        return lat, lon
                
                break  # If ffprobe worked, don't try other paths
                
            except subprocess.TimeoutExpired:
                self.logger.warning(f"ffprobe timeout extracting GPS from {filepath}")
                continue
            except FileNotFoundError:
                continue
            except Exception as e:
                self.logger.error(f"Error extracting video GPS from {filepath}: {e}")
                continue
        
        return None, None
    
    def _get_gps_coordinate(self, gps_info: Dict[Any, Any], coord_key: int, ref_key: int) -> Optional[float]:
        """
        Convert GPS coordinate from EXIF format to decimal degrees.
        
        Args:
            gps_info: GPS information dictionary from EXIF
            coord_key: Key for coordinate data (2=lat, 4=lon)
            ref_key: Key for reference data (1=lat_ref, 3=lon_ref)
            
        Returns:
            Decimal coordinate or None if conversion fails
        """
        try:
            coord = gps_info.get(coord_key)
            ref = gps_info.get(ref_key)
            
            if coord and ref:
                # Handle coordinate format: [degrees, minutes, seconds]
                if isinstance(coord, (list, tuple)) and len(coord) >= 3:
                    degrees = float(coord[0])
                    minutes = float(coord[1]) if coord[1] else 0
                    seconds = float(coord[2]) if coord[2] else 0
                    
                    # Convert to decimal degrees
                    decimal = degrees + minutes/60 + seconds/3600
                    
                    # Apply direction (South/West are negative)
                    if ref in ['S', 'W']:
                        decimal = -decimal
                    
                    return decimal
            
            return None
            
        except Exception as e:
            self.logger.error(f"GPS coordinate conversion error: {e}")
            print(f"GPS coordinate conversion error: {e}")
            return None
    
    def _get_city_from_coords_cached(self, lat: float, lon: float) -> str:
        """
        Convert GPS coordinates to city name using cache and API with retry logic.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            City name or empty string if lookup fails
        """
        # First check cache
        cached_city = self.city_cache.get_city(lat, lon)
        if cached_city:
            self.logger.debug(f"Cache hit for coordinates {lat}, {lon}: {cached_city}")
            return cached_city
        
        # Lookups are paused after repeated HTTP 429s: skip instead of stalling.
        # Nothing is cached, so the city is retried on the next run.
        if _nominatim_limiter.is_blocked():
            self.logger.warning(
                f"City lookup skipped for {lat}, {lon}: OpenStreetMap rate-limit pause")
            return ""

        # Cache miss - try API with retry logic
        self.logger.debug(f"Cache miss for coordinates {lat}, {lon}, trying API")
        city = self._get_city_from_coords_with_retry(lat, lon)
        
        # Cache the result if successful
        if city:
            self.city_cache.set_city(lat, lon, city, "nominatim_api")
            self.logger.debug(f"Cached city for {lat}, {lon}: {city}")
        
        return city
    
    def _get_city_from_coords_with_retry(self, lat: float, lon: float) -> str:
        """
        Convert GPS coordinates to city name using OpenStreetMap API with error recovery.
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            City name or empty string if lookup fails
        """
        self.logger.debug(f"Making API call for coordinates {lat}, {lon}")
        
        def api_call():
            # Use OpenStreetMap Nominatim API for reverse geocoding
            url = (f"https://nominatim.openstreetmap.org/reverse?"
                   f"format=json&lat={lat}&lon={lon}&zoom=10&"
                   f"addressdetails=1&accept-language=en")
            
            self.logger.debug(f"API request URL: {url}")
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'MediaRenamer/1.0')
            
            # Respect Nominatim's usage policy (max 1 request/second) and any
            # back-off imposed after an HTTP 429.
            if _nominatim_limiter.is_blocked():
                raise RuntimeError("OpenStreetMap lookups paused after repeated rate limiting")
            _nominatim_limiter.wait_turn(self.network_wait_callback)
            try:
                with urllib.request.urlopen(req, timeout=self.network_timeout) as response:
                    response_data = response.read().decode()
                    self.logger.debug(f"API response received: {len(response_data)} characters")
                    data = json.loads(response_data)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry_after = e.headers.get('Retry-After') if e.headers else None
                    wait = _nominatim_limiter.note_rate_limited(
                        int(retry_after) if retry_after and retry_after.isdigit() else None)
                    self.logger.warning(
                        f"OpenStreetMap rate limit (HTTP 429): holding city lookups for {wait}s")
                raise
            _nominatim_limiter.note_success()
            
            # Validate API response
            if not isinstance(data, dict):
                raise ValueError(f"Invalid API response format: {data}")
            
            address = data.get('address', {})
            
            # Get city name in priority order
            city = (address.get('city') or 
                   address.get('town') or 
                   address.get('village') or 
                   address.get('municipality'))
            
            # Clean up city name
            if city:
                city = self._clean_city_name(city)
            
            # The county fallback needs the same cleaning as a city name
            county = address.get('county', '')
            result = city or (self._clean_city_name(county) if county else '')
            
            if result:
                self.logger.info(f"Successfully retrieved city for {lat}, {lon}: {result}")
            else:
                self.logger.warning(f"API returned no city data for {lat}, {lon}")
            
            return result
        
        # Try API call with retry logic
        self.logger.info(f"Starting GPS API lookup for coordinates {lat}, {lon}")
        api_result = self.error_recovery.retry_with_backoff(api_call)
        
        if api_result.success:
            self.logger.info(f"GPS API lookup successful for {lat}, {lon}")
            return api_result.result or ""
        
        # Handle network error with potential cached fallback
        self.logger.warning(f"GPS API lookup failed for {lat}, {lon}: {api_result.error}")
        cached_city = self.city_cache.get_city(lat, lon) if self.city_cache else None
        fallback_result = self.error_recovery.handle_network_error(
            api_result.error, 
            f"GPS lookup for {lat}, {lon}",
            cached_city
        )
        
        if fallback_result.success:
            self.logger.info(f"Using fallback result for {lat}, {lon}: {fallback_result.result}")
            return fallback_result.result or ""
        
        # Handle GPS API error for invalid responses
        if isinstance(api_result.error, (json.JSONDecodeError, ValueError)):
            self.logger.error(f"Invalid GPS API response for {lat}, {lon}: {api_result.error}")
            gps_error_result = self.error_recovery.handle_gps_api_error(
                api_result.error,
                str(api_result.error)
            )
            return gps_error_result.result or ""
        
        self.logger.error(f"All GPS lookup attempts failed for {lat}, {lon}")
        return ""
    
    def _clean_city_name(self, city_name: str) -> str:
        """
        Clean up city names by removing administrative prefixes and suffixes to get common names.
        
        Args:
            city_name: Raw city name from geocoding service
            
        Returns:
            Cleaned city name using commonly used form
        """
        original_name = city_name
        cleaned = city_name.strip()
        
        # Case-insensitive prefix/suffix removal patterns
        # Each tuple: (pattern, replacement, case_sensitive)
        cleanup_patterns = [
            # English patterns
            ('Capital City of ', '', False),
            ('Capital city of ', '', False),
            ('City of ', '', False),
            ('Municipality of ', '', False),
            ('Municipal Unit of ', '', False),
            ('Municipa Unit of ', '', False),  # typo seen in OSM data
            ('Borough of ', '', False),
            ('Town of ', '', False),
            ('Village of ', '', False),
            ('District of ', '', False),
            ('County of ', '', False),
            ('Province of ', '', False),
            ('State of ', '', False),
            ('Region of ', '', False),
            
            # Common suffixes
            (' Municipal Unit', '', False),
            (' Municipality', '', False),
            (' City', '', False),
            (' Borough', '', False),
            (' District', '', False),
            (' County', '', False),
            (' Province', '', False),
            (' Region', '', False),
            (' Metropolitan Area', '', False),
            (' Metro Area', '', False),
            (' Urban Area', '', False),
            
            # Greek patterns (keeping existing ones)
            ('Δημοτική Κοινότητα Καρλοβασίου', 'Karlovasi', True),
            ('Δημοτική Κοινότητα ', '', True),
            ('Δημοτική Ενότητα ', '', True),
            ('Δημοτικό Διαμέρισμα ', '', True),
            ('Κοινότητα ', '', True),
            ('Δήμος ', '', True),
            
            # German patterns
            ('Stadt ', '', False),
            ('Gemeinde ', '', False),
            ('Kreis ', '', False),
            
            # French patterns
            ('Ville de ', '', False),
            ('Commune de ', '', False),
            
            # Spanish patterns
            ('Ciudad de ', '', False),
            ('Municipio de ', '', False),
            
            # Italian patterns
            ('Città di ', '', False),
            ('Comune di ', '', False),
            
            # Portuguese patterns
            ('Cidade de ', '', False),
            ('Município de ', '', False),
            
            # Dutch patterns
            ('Gemeente ', '', False),
            
            # Czech patterns
            ('Hlavní město ', '', False),  # Capital city
            
            # Polish patterns
            ('Miasto ', '', False),
            ('Gmina ', '', False),
        ]
        
        # Apply cleanup patterns
        for pattern, replacement, case_sensitive in cleanup_patterns:
            if case_sensitive:
                if cleaned.startswith(pattern):
                    cleaned = cleaned.replace(pattern, replacement, 1).strip()
                elif cleaned.endswith(pattern.strip()):
                    cleaned = cleaned.replace(pattern.strip(), replacement, 1).strip()
            else:
                # Case-insensitive matching
                if cleaned.lower().startswith(pattern.lower()):
                    # Find the actual case in the original string
                    start_idx = len(pattern)
                    cleaned = cleaned[start_idx:].strip()
                elif cleaned.lower().endswith(pattern.strip().lower()):
                    # Remove suffix
                    end_idx = len(cleaned) - len(pattern.strip())
                    cleaned = cleaned[:end_idx].strip()
        
        # Additional cleanup for special cases
        cleaned = self._apply_special_city_cleanups(cleaned)

        # Keep filenames portable: render anything non-Latin in Latin letters.
        cleaned = to_latin(cleaned)
        
        # Ensure we don't return empty string
        result = cleaned if cleaned else city_name
        
        if result != original_name:
            self.logger.debug(f"Cleaned city name: '{original_name}' -> '{result}'")
        
        return result
    
    def _apply_special_city_cleanups(self, city_name: str) -> str:
        """
        Apply special case cleanups for specific city names.
        
        Args:
            city_name: City name to clean
            
        Returns:
            Cleaned city name
        """
        # Special case mappings for commonly misnamed cities
        special_cases = {
            # Case-insensitive mappings
            'prague': 'Prague',
            'praha': 'Prague',
            'wien': 'Vienna',
            'münchen': 'Munich',
            'köln': 'Cologne',
            'firenze': 'Florence',
            'roma': 'Rome',
            'milano': 'Milan',
            'venezia': 'Venice',
            'napoli': 'Naples',
            'lisboa': 'Lisbon',
            'warszawa': 'Warsaw',
            'moskva': 'Moscow',
            'sankt-peterburg': 'Saint Petersburg',
            'beijing': 'Beijing',
            'tokyo': 'Tokyo',
            'new york city': 'New York',
            'los angeles': 'Los Angeles',
            'san francisco': 'San Francisco',
        }
        
        # Check for special case mappings (case-insensitive)
        city_lower = city_name.lower()
        for key, value in special_cases.items():
            if city_lower == key:
                return value
        
        # Remove common administrative words that might remain
        administrative_words = [
            'administrative', 'admin', 'metropolitan', 'metro', 'urban',
            'greater', 'central', 'downtown', 'inner', 'outer'
        ]
        
        words = city_name.split()
        filtered_words = []
        
        for word in words:
            if word.lower() not in administrative_words:
                filtered_words.append(word)
        
        # If we filtered out all words, return original
        if not filtered_words:
            return city_name
        
        return ' '.join(filtered_words)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get city cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        return self.city_cache.get_cache_stats()
    
    def save_cache(self) -> bool:
        """
        Save the city cache to disk.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            success = self.city_cache.save_cache()
            if success:
                self.logger.info("City cache saved successfully")
            else:
                self.logger.error("Failed to save city cache")
            return success
        except Exception as e:
            self.logger.error(f"Error saving city cache: {e}")
            return False
    
    def load_cache(self) -> bool:
        """
        Load the city cache from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            success = self.city_cache.load_cache()
            if success:
                stats = self.get_cache_stats()
                self.logger.info(f"City cache loaded successfully: {stats['total_entries']} entries")
            else:
                self.logger.warning("Failed to load city cache, starting with empty cache")
            return success
        except Exception as e:
            self.logger.error(f"Error loading city cache: {e}")
            return False