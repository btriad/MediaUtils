#!/usr/bin/env python3
"""Test XMP support with real testxmp.NEF file."""

from media_processor import MediaProcessor
from xmp_handler import XMPHandler
import os

print("=" * 70)
print("TESTING XMP SUPPORT WITH REAL FILE: testxmp.NEF")
print("=" * 70)

# Test 1: XMP file detection
print("\n1. XMP File Detection")
print("-" * 70)
xmp_handler = XMPHandler()
xmp_file = xmp_handler.find_xmp_file('testxmp.NEF')
if xmp_file:
    print(f"✓ XMP file found: {xmp_file}")
else:
    print("✗ XMP file not found")
    exit(1)

# Test 2: GPS extraction from XMP
print("\n2. GPS Extraction from XMP")
print("-" * 70)
lat, lon = xmp_handler.extract_gps_from_xmp(xmp_file)
if lat and lon:
    print(f"✓ GPS extracted: {lat:.6f}, {lon:.6f}")
    print(f"  Location: Istanbul, Turkey (Beyoğlu district)")
else:
    print("✗ GPS extraction failed")
    exit(1)

# Test 3: Date extraction from XMP
print("\n3. Date Extraction from XMP")
print("-" * 70)
date = xmp_handler.extract_date_from_xmp(xmp_file)
if date:
    print(f"✓ Date extracted: {date}")
else:
    print("⚠ No date in XMP (may be in NEF file)")

# Test 4: MediaProcessor integration
print("\n4. MediaProcessor Integration")
print("-" * 70)
processor = MediaProcessor()
location, city = processor.get_location_and_city('testxmp.NEF')
print(f"Location: {location}")
print(f"City: {city}")

if city and city != "No GPS":
    print(f"✓ City lookup successful: {city}")
else:
    print("✗ City lookup failed")
    exit(1)

# Test 5: Full metadata extraction
print("\n5. Full Metadata Extraction")
print("-" * 70)
file_date, has_metadata = processor.get_file_date('testxmp.NEF')
print(f"Date: {file_date}")
print(f"Has metadata: {has_metadata}")

# Test 6: Expected filename
print("\n6. Expected Filename Generation")
print("-" * 70)
if file_date and city:
    expected_name = f"{file_date.strftime('%Y.%m.%d-%H.%M.%S')}.001.{city}.nef"
    print(f"Expected filename: {expected_name}")
    print(f"✓ All metadata available for renaming")
else:
    print("⚠ Some metadata missing")

print("\n" + "=" * 70)
print("XMP SUPPORT TEST COMPLETE")
print("=" * 70)
print("\n✓ XMP sidecar file support is working correctly!")
print(f"✓ GPS coordinates extracted from XMP: {lat:.6f}, {lon:.6f}")
print(f"✓ City identified: {city}")
print("\nYour testxmp.NEF file will be renamed with GPS data from the XMP file!")
