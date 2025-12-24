"""
XMP Sidecar File Handler

Handles extraction of metadata from XMP sidecar files and renaming them
alongside their associated RAW image files.

XMP files are XML-based sidecar files created by Adobe Lightroom, Camera Raw,
and other photo editing software to store metadata separately from the original file.
"""

import os
import xml.etree.ElementTree as ET
from typing import Optional, Tuple
from datetime import datetime
import logging


class XMPHandler:
    """Handler for XMP sidecar files."""
    
    # XMP namespaces
    NAMESPACES = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'exif': 'http://ns.adobe.com/exif/1.0/',
        'tiff': 'http://ns.adobe.com/tiff/1.0/',
        'xmp': 'http://ns.adobe.com/xap/1.0/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
        'Iptc4xmpCore': 'http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/',
        'exifEX': 'http://cipa.jp/exif/1.0/'
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize XMP handler.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def find_xmp_file(self, image_path: str) -> Optional[str]:
        """
        Find XMP sidecar file for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Path to XMP file if found, None otherwise
        """
        # Try common XMP naming patterns
        base_path = os.path.splitext(image_path)[0]
        
        # Pattern 1: same name with .xmp extension
        xmp_path = f"{base_path}.xmp"
        if os.path.exists(xmp_path):
            return xmp_path
        
        # Pattern 2: same name with .XMP extension (uppercase)
        xmp_path = f"{base_path}.XMP"
        if os.path.exists(xmp_path):
            return xmp_path
        
        # Pattern 3: original_name.ext.xmp (e.g., photo.nef.xmp)
        xmp_path = f"{image_path}.xmp"
        if os.path.exists(xmp_path):
            return xmp_path
        
        # Pattern 4: original_name.ext.XMP
        xmp_path = f"{image_path}.XMP"
        if os.path.exists(xmp_path):
            return xmp_path
        
        return None
    
    def extract_gps_from_xmp(self, xmp_path: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Extract GPS coordinates from XMP file.
        
        Args:
            xmp_path: Path to XMP file
            
        Returns:
            Tuple of (latitude, longitude) or (None, None) if not found
        """
        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()
            
            # Register namespaces
            for prefix, uri in self.NAMESPACES.items():
                ET.register_namespace(prefix, uri)
            
            # Look for GPS data in exif namespace
            # XMP stores GPS as decimal degrees directly or in element text or attributes
            lat = None
            lon = None
            
            # Try 1: Check element text
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                
                if tag == 'GPSLatitude' and elem.text:
                    try:
                        lat = self._parse_gps_coordinate(elem.text)
                    except:
                        pass
                
                elif tag == 'GPSLongitude' and elem.text:
                    try:
                        lon = self._parse_gps_coordinate(elem.text)
                    except:
                        pass
            
            if lat is not None and lon is not None:
                self.logger.info(f"Extracted GPS from XMP {os.path.basename(xmp_path)}: {lat:.6f}, {lon:.6f}")
                return lat, lon
            
            # Try 2: Check element attributes (common in some XMP formats)
            for elem in root.iter():
                for attr_name, attr_value in elem.attrib.items():
                    attr_tag = attr_name.split('}')[-1] if '}' in attr_name else attr_name
                    
                    if attr_tag == 'GPSLatitude':
                        try:
                            lat = self._parse_gps_coordinate(attr_value)
                        except:
                            pass
                    
                    elif attr_tag == 'GPSLongitude':
                        try:
                            lon = self._parse_gps_coordinate(attr_value)
                        except:
                            pass
            
            if lat is not None and lon is not None:
                self.logger.info(f"Extracted GPS from XMP attributes {os.path.basename(xmp_path)}: {lat:.6f}, {lon:.6f}")
                return lat, lon
            
            # Try 3: Alternative format: exifEX:GPSLatitude
            for elem in root.iter('{http://cipa.jp/exif/1.0/}GPSLatitude'):
                if elem.text:
                    try:
                        lat = self._parse_gps_coordinate(elem.text)
                    except:
                        pass
            
            for elem in root.iter('{http://cipa.jp/exif/1.0/}GPSLongitude'):
                if elem.text:
                    try:
                        lon = self._parse_gps_coordinate(elem.text)
                    except:
                        pass
            
            if lat is not None and lon is not None:
                self.logger.info(f"Extracted GPS from XMP (exifEX) {os.path.basename(xmp_path)}: {lat:.6f}, {lon:.6f}")
                return lat, lon
            
            self.logger.debug(f"No GPS coordinates found in XMP: {os.path.basename(xmp_path)}")
            return None, None
            
        except ET.ParseError as e:
            self.logger.warning(f"Failed to parse XMP file {xmp_path}: {e}")
            return None, None
        except Exception as e:
            self.logger.error(f"Error extracting GPS from XMP {xmp_path}: {e}")
            return None, None
    
    def _parse_gps_coordinate(self, coord_str: str) -> Optional[float]:
        """
        Parse GPS coordinate from XMP string format.
        
        XMP can store GPS in various formats:
        - Decimal: "38.015"
        - With direction: "38.015N" or "38.015,N"
        - DMS format: "38,0,54N" (degrees, minutes, seconds)
        - Degrees and decimal minutes: "41,2.2093320N" (degrees, decimal minutes)
        
        Args:
            coord_str: GPS coordinate string
            
        Returns:
            Decimal coordinate or None
        """
        if not coord_str:
            return None
        
        coord_str = coord_str.strip()
        
        # Check for direction suffix
        direction = None
        if coord_str[-1] in ['N', 'S', 'E', 'W']:
            direction = coord_str[-1]
            coord_str = coord_str[:-1].strip(',').strip()
        
        # Try parsing as decimal
        try:
            value = float(coord_str)
            
            # Apply direction
            if direction in ['S', 'W']:
                value = -value
            
            return value
        except ValueError:
            pass
        
        # Try parsing as degrees, minutes (and optionally seconds)
        try:
            parts = coord_str.split(',')
            if len(parts) == 2:
                # Degrees and decimal minutes format: "41,2.2093320"
                degrees = float(parts[0])
                minutes = float(parts[1])
                
                value = degrees + (minutes / 60.0)
                
                # Apply direction
                if direction in ['S', 'W']:
                    value = -value
                
                return value
            elif len(parts) == 3:
                # DMS format: "41,2,13.56"
                degrees = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                
                value = degrees + (minutes / 60.0) + (seconds / 3600.0)
                
                # Apply direction
                if direction in ['S', 'W']:
                    value = -value
                
                return value
        except:
            pass
        
        return None
    
    def extract_date_from_xmp(self, xmp_path: str) -> Optional[datetime]:
        """
        Extract date/time from XMP file.
        
        Args:
            xmp_path: Path to XMP file
            
        Returns:
            datetime object or None if not found
        """
        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()
            
            # Try different date fields in order of preference
            date_fields = [
                '{http://ns.adobe.com/exif/1.0/}DateTimeOriginal',
                '{http://ns.adobe.com/exif/1.0/}DateTimeDigitized',
                '{http://ns.adobe.com/xap/1.0/}CreateDate',
                '{http://ns.adobe.com/xap/1.0/}ModifyDate',
                '{http://ns.adobe.com/photoshop/1.0/}DateCreated'
            ]
            
            for field in date_fields:
                for elem in root.iter(field):
                    if elem.text:
                        try:
                            # XMP dates are typically in ISO 8601 format
                            # e.g., "2024-03-14T11:56:10" or "2024-03-14T11:56:10+02:00"
                            date_str = elem.text.split('+')[0].split('-')[0:3]  # Remove timezone
                            date_str = elem.text.split('.')[0]  # Remove milliseconds
                            
                            # Try different date formats
                            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                                try:
                                    parsed_date = datetime.strptime(elem.text.split('+')[0].split('.')[0], fmt)
                                    self.logger.debug(f"Extracted date from XMP: {parsed_date}")
                                    return parsed_date
                                except ValueError:
                                    continue
                        except Exception as e:
                            self.logger.debug(f"Failed to parse date from XMP field {field}: {e}")
                            continue
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting date from XMP {xmp_path}: {e}")
            return None
    
    def rename_xmp_with_image(self, old_image_path: str, new_image_path: str) -> bool:
        """
        Rename XMP sidecar file to match renamed image file.
        
        Args:
            old_image_path: Original image file path
            new_image_path: New image file path
            
        Returns:
            True if XMP was renamed, False if no XMP or rename failed
        """
        # Find XMP file for old image
        xmp_path = self.find_xmp_file(old_image_path)
        
        if not xmp_path:
            self.logger.debug(f"No XMP file found for {os.path.basename(old_image_path)}")
            return False
        
        # Determine new XMP path based on naming pattern
        old_base = os.path.splitext(old_image_path)[0]
        new_base = os.path.splitext(new_image_path)[0]
        
        # Preserve the XMP naming pattern
        if xmp_path == f"{old_base}.xmp":
            new_xmp_path = f"{new_base}.xmp"
        elif xmp_path == f"{old_base}.XMP":
            new_xmp_path = f"{new_base}.XMP"
        elif xmp_path == f"{old_image_path}.xmp":
            new_xmp_path = f"{new_image_path}.xmp"
        elif xmp_path == f"{old_image_path}.XMP":
            new_xmp_path = f"{new_image_path}.XMP"
        else:
            # Default to lowercase .xmp
            new_xmp_path = f"{new_base}.xmp"
        
        try:
            os.rename(xmp_path, new_xmp_path)
            self.logger.info(f"Renamed XMP: {os.path.basename(xmp_path)} -> {os.path.basename(new_xmp_path)}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to rename XMP file {xmp_path}: {e}")
            return False
