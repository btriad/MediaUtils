#!/usr/bin/env python3
"""Detailed GPS check for NEF files."""

import exifread
import sys

if len(sys.argv) < 2:
    print("Usage: python check_gps_detailed.py <nef_file>")
    sys.exit(1)

filename = sys.argv[1]

print(f"Checking GPS data in: {filename}")
print("=" * 70)

with open(filename, 'rb') as f:
    tags = exifread.process_file(f, details=True)

# Check for all possible GPS tags
gps_tag_names = [
    'GPS GPSVersionID',
    'GPS GPSLatitudeRef',
    'GPS GPSLatitude',
    'GPS GPSLongitudeRef',
    'GPS GPSLongitude',
    'GPS GPSAltitudeRef',
    'GPS GPSAltitude',
    'GPS GPSTimeStamp',
    'GPS GPSSatellites',
    'GPS GPSStatus',
    'GPS GPSMeasureMode',
    'GPS GPSDOP',
    'GPS GPSSpeedRef',
    'GPS GPSSpeed',
    'GPS GPSTrackRef',
    'GPS GPSTrack',
    'GPS GPSImgDirectionRef',
    'GPS GPSImgDirection',
    'GPS GPSMapDatum',
    'GPS GPSDestLatitudeRef',
    'GPS GPSDestLatitude',
    'GPS GPSDestLongitudeRef',
    'GPS GPSDestLongitude',
    'GPS GPSDestBearingRef',
    'GPS GPSDestBearing',
    'GPS GPSDestDistanceRef',
    'GPS GPSDestDistance',
    'GPS GPSProcessingMethod',
    'GPS GPSAreaInformation',
    'GPS GPSDateStamp',
    'GPS GPSDifferential',
    'GPS GPSHPositioningError'
]

print("\nGPS Tags Found:")
print("-" * 70)

found_tags = []
for tag_name in gps_tag_names:
    if tag_name in tags:
        found_tags.append(tag_name)
        print(f"✓ {tag_name}: {tags[tag_name]}")

if not found_tags:
    print("❌ NO GPS TAGS FOUND")
else:
    print(f"\nTotal GPS tags found: {len(found_tags)}")

# Check for required coordinate tags
print("\n" + "=" * 70)
print("COORDINATE CHECK:")
print("=" * 70)

required = ['GPS GPSLatitude', 'GPS GPSLongitude', 'GPS GPSLatitudeRef', 'GPS GPSLongitudeRef']
missing = [tag for tag in required if tag not in tags]

if missing:
    print(f"❌ MISSING REQUIRED TAGS: {', '.join(missing)}")
    print("\nThis file does NOT contain GPS coordinates.")
else:
    print("✓ All required GPS coordinate tags present!")
    print(f"\nLatitude: {tags['GPS GPSLatitude']} {tags['GPS GPSLatitudeRef']}")
    print(f"Longitude: {tags['GPS GPSLongitude']} {tags['GPS GPSLongitudeRef']}")
