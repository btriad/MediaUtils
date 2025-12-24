#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot GPS extraction from NEF files.

This script will:
1. Check if exifread is available
2. Try to extract GPS data using different methods
3. Show all available EXIF tags
4. Provide detailed debugging information
"""

import os
import sys
from media_processor import MediaProcessor, EXIFREAD_AVAILABLE
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

try:
    import exifread
except ImportError:
    exifread = None


def diagnose_nef_file(filepath):
    """Diagnose GPS extraction from a NEF file."""
    print("=" * 70)
    print(f"DIAGNOSING NEF FILE: {os.path.basename(filepath)}")
    print("=" * 70)
    
    if not os.path.exists(filepath):
        print(f"❌ ERROR: File not found: {filepath}")
        return
    
    # Check file extension
    ext = os.path.splitext(filepath.lower())[1]
    print(f"\n1. FILE INFO")
    print(f"   Extension: {ext}")
    print(f"   Size: {os.path.getsize(filepath):,} bytes")
    
    # Check exifread availability
    print(f"\n2. LIBRARY STATUS")
    print(f"   exifread available: {EXIFREAD_AVAILABLE}")
    print(f"   PIL/Pillow available: True")
    
    # Try Method 1: exifread (recommended for RAW)
    print(f"\n3. METHOD 1: EXIFREAD EXTRACTION")
    if exifread:
        try:
            with open(filepath, 'rb') as f:
                tags = exifread.process_file(f, details=False)
            
            print(f"   Total EXIF tags found: {len(tags)}")
            
            # Look for GPS tags
            gps_tags = {k: v for k, v in tags.items() if k.startswith('GPS')}
            print(f"   GPS tags found: {len(gps_tags)}")
            
            if gps_tags:
                print("\n   GPS Tags:")
                for tag, value in gps_tags.items():
                    print(f"      {tag}: {value}")
                
                # Try to extract coordinates
                gps_lat = tags.get('GPS GPSLatitude')
                gps_lat_ref = tags.get('GPS GPSLatitudeRef')
                gps_lon = tags.get('GPS GPSLongitude')
                gps_lon_ref = tags.get('GPS GPSLongitudeRef')
                
                if gps_lat and gps_lon:
                    print("\n   ✓ GPS coordinates found!")
                    print(f"      Latitude: {gps_lat} {gps_lat_ref}")
                    print(f"      Longitude: {gps_lon} {gps_lon_ref}")
                    
                    # Try conversion
                    try:
                        processor = MediaProcessor()
                        lat = processor._convert_gps_to_decimal(gps_lat.values, str(gps_lat_ref))
                        lon = processor._convert_gps_to_decimal(gps_lon.values, str(gps_lon_ref))
                        print(f"\n   Decimal coordinates:")
                        print(f"      Latitude: {lat}")
                        print(f"      Longitude: {lon}")
                    except Exception as e:
                        print(f"\n   ❌ Conversion failed: {e}")
                else:
                    print("\n   ⚠ GPS latitude/longitude tags not found")
            else:
                print("\n   ⚠ No GPS tags found in EXIF data")
                print("\n   This could mean:")
                print("      - Camera doesn't have GPS")
                print("      - GPS was disabled when photo was taken")
                print("      - GPS data was stripped from the file")
            
        except Exception as e:
            print(f"   ❌ exifread extraction failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("   ⚠ exifread not available - install with: pip install exifread")
    
    # Try Method 2: PIL/Pillow
    print(f"\n4. METHOD 2: PIL/PILLOW EXTRACTION")
    try:
        with Image.open(filepath) as img:
            exif = img.getexif()
            
            if exif:
                print(f"   Total EXIF tags found: {len(exif)}")
                
                # Try to get GPS IFD
                gps_info = None
                try:
                    gps_info = exif.get_ifd(0x8825)  # GPS IFD tag
                    print(f"   GPS IFD found: {gps_info is not None}")
                except Exception as e:
                    print(f"   GPS IFD access failed: {e}")
                
                if gps_info:
                    print(f"   GPS tags in IFD: {len(gps_info)}")
                    print("\n   GPS Data:")
                    for tag_id, value in gps_info.items():
                        tag_name = GPSTAGS.get(tag_id, tag_id)
                        print(f"      {tag_name} ({tag_id}): {value}")
                    
                    # Try to extract coordinates
                    try:
                        processor = MediaProcessor()
                        lat = processor._get_gps_coordinate(gps_info, 2, 1)
                        lon = processor._get_gps_coordinate(gps_info, 4, 3)
                        
                        if lat and lon:
                            print(f"\n   ✓ GPS coordinates extracted!")
                            print(f"      Latitude: {lat}")
                            print(f"      Longitude: {lon}")
                        else:
                            print(f"\n   ⚠ Could not extract coordinates from GPS IFD")
                    except Exception as e:
                        print(f"\n   ❌ Coordinate extraction failed: {e}")
                else:
                    print("\n   ⚠ No GPS IFD found")
                    
                    # Show all available tags
                    print("\n   Available EXIF tags (first 20):")
                    count = 0
                    for tag_id, value in exif.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        print(f"      {tag_name} ({tag_id}): {str(value)[:50]}")
                        count += 1
                        if count >= 20:
                            print(f"      ... and {len(exif) - 20} more tags")
                            break
            else:
                print("   ⚠ No EXIF data found")
                
    except Exception as e:
        print(f"   ❌ PIL extraction failed: {e}")
        print(f"   This is normal for some RAW formats that PIL can't read")
    
    # Try Method 3: MediaProcessor (integrated approach)
    print(f"\n5. METHOD 3: MEDIAPROCESSOR (INTEGRATED)")
    try:
        processor = MediaProcessor()
        lat, lon = processor.get_location_and_city(filepath)
        
        if lat and lat != "No GPS":
            print(f"   ✓ Location extracted successfully!")
            print(f"      Location: {lat}")
        else:
            print(f"   ⚠ No GPS location found")
            print(f"      Result: {lat}")
    except Exception as e:
        print(f"   ❌ MediaProcessor extraction failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Recommendations
    print(f"\n6. RECOMMENDATIONS")
    if not EXIFREAD_AVAILABLE:
        print("   ⚠ CRITICAL: Install exifread for better RAW support")
        print("      Command: pip install exifread")
    
    print("\n   To verify GPS data in your NEF file:")
    print("   1. Open the file in your camera manufacturer's software")
    print("   2. Check if GPS data is present")
    print("   3. Verify GPS was enabled when photo was taken")
    print("   4. Some cameras require external GPS accessory")
    
    print("\n" + "=" * 70)


def main():
    """Main diagnostic function."""
    print("\nNEF GPS EXTRACTION DIAGNOSTIC TOOL")
    print("=" * 70)
    
    if len(sys.argv) < 2:
        print("\nUsage: python diagnose_nef_gps.py <path_to_nef_file>")
        print("\nExample:")
        print("  python diagnose_nef_gps.py DSC_1234.NEF")
        print("  python diagnose_nef_gps.py \"C:\\Photos\\IMG_5678.NEF\"")
        
        # Try to find NEF files in current directory
        print("\nSearching for NEF files in current directory...")
        nef_files = [f for f in os.listdir('.') if f.lower().endswith('.nef')]
        
        if nef_files:
            print(f"\nFound {len(nef_files)} NEF file(s):")
            for i, f in enumerate(nef_files[:5], 1):
                print(f"  {i}. {f}")
            
            if len(nef_files) > 5:
                print(f"  ... and {len(nef_files) - 5} more")
            
            print("\nRun again with a filename:")
            print(f"  python diagnose_nef_gps.py \"{nef_files[0]}\"")
        else:
            print("No NEF files found in current directory.")
        
        return
    
    filepath = sys.argv[1]
    
    # Handle multiple files
    if os.path.isdir(filepath):
        print(f"\nScanning directory: {filepath}")
        nef_files = [f for f in os.listdir(filepath) if f.lower().endswith('.nef')]
        print(f"Found {len(nef_files)} NEF file(s)")
        
        if nef_files:
            print("\nDiagnosing first file as example...")
            diagnose_nef_file(os.path.join(filepath, nef_files[0]))
            
            if len(nef_files) > 1:
                print(f"\n\nTo diagnose other files, run:")
                for f in nef_files[1:3]:
                    print(f"  python diagnose_nef_gps.py \"{os.path.join(filepath, f)}\"")
    else:
        diagnose_nef_file(filepath)


if __name__ == "__main__":
    main()
