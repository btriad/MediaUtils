#!/usr/bin/env python3
"""Check all EXIF tags in the NEF file."""

import exifread

with open('test.nef', 'rb') as f:
    tags = exifread.process_file(f, details=True)

print("ALL EXIF TAGS IN test.nef:")
print("=" * 70)

# Group tags by category
categories = {}
for tag, value in tags.items():
    category = tag.split()[0] if ' ' in tag else 'Other'
    if category not in categories:
        categories[category] = []
    categories[category].append((tag, value))

# Print by category
for category in sorted(categories.keys()):
    print(f"\n{category} Tags:")
    print("-" * 70)
    for tag, value in sorted(categories[category]):
        print(f"  {tag}: {value}")

# Specifically check for GPS tags
print("\n" + "=" * 70)
print("GPS-RELATED TAGS:")
print("=" * 70)
gps_tags = {k: v for k, v in tags.items() if 'GPS' in k}
if gps_tags:
    for tag, value in sorted(gps_tags.items()):
        print(f"  {tag}: {value}")
else:
    print("  NO GPS TAGS FOUND")

print("\n" + "=" * 70)
print("CONCLUSION:")
print("=" * 70)

required_gps_tags = ['GPS GPSLatitude', 'GPS GPSLongitude', 'GPS GPSLatitudeRef', 'GPS GPSLongitudeRef']
missing_tags = [tag for tag in required_gps_tags if tag not in tags]

if missing_tags:
    print(f"❌ This NEF file does NOT contain GPS coordinates")
    print(f"   Missing tags: {', '.join(missing_tags)}")
    print(f"\n   This means:")
    print(f"   - GPS was not enabled when photo was taken")
    print(f"   - OR GPS had not locked onto satellites")
    print(f"   - OR GPS data was removed from the file")
else:
    print(f"✓ This NEF file DOES contain GPS coordinates")
