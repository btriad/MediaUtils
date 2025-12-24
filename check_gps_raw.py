#!/usr/bin/env python3
"""Check raw GPS IFD data."""

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import sys

if len(sys.argv) < 2:
    print("Usage: python check_gps_raw.py <nef_file>")
    sys.exit(1)

filename = sys.argv[1]

print(f"Checking raw GPS IFD in: {filename}")
print("=" * 70)

try:
    with Image.open(filename) as img:
        exif = img.getexif()
        
        if not exif:
            print("No EXIF data found")
            sys.exit(1)
        
        print(f"Total EXIF tags: {len(exif)}")
        
        # Try to get GPS IFD
        try:
            gps_ifd = exif.get_ifd(0x8825)
            print(f"\n✓ GPS IFD found with {len(gps_ifd)} entries")
            
            print("\nGPS IFD Contents:")
            print("-" * 70)
            for tag_id, value in gps_ifd.items():
                tag_name = GPSTAGS.get(tag_id, f"Unknown_{tag_id}")
                print(f"  Tag {tag_id} ({tag_name}): {value}")
                print(f"    Type: {type(value)}")
                print(f"    Value: {repr(value)}")
                
        except Exception as e:
            print(f"❌ Could not access GPS IFD: {e}")
            
except Exception as e:
    print(f"❌ Error opening file: {e}")
    import traceback
    traceback.print_exc()
