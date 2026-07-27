#!/usr/bin/env python3
"""
Test metadata extraction from iPhone MOV file.
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from media_processor import MediaProcessor
from city_cache import CityCache

def test_iphone_mov():
    """Test the test.MOV file."""
    
    print("🎬 TESTING IPHONE MOV FILE: test.MOV")
    print("=" * 60)
    
    test_file = "test.MOV"
    
    # Check if file exists
    if not os.path.exists(test_file):
        print(f"❌ File not found: {test_file}")
        print("Please make sure test.MOV is in the current directory")
        return
    
    print(f"✓ File found: {test_file}")
    print(f"  File size: {os.path.getsize(test_file):,} bytes")
    
    # Initialize processor
    cache = CityCache("test_cache.json")
    processor = MediaProcessor(city_cache=cache)
    
    print("\n1. CHECKING FILE SUPPORT:")
    print("-" * 40)
    is_supported = processor.is_supported_file(test_file)
    print(f"   Is supported: {is_supported}")
    
    print("\n2. EXTRACTING DATE/TIME:")
    print("-" * 40)
    file_date, has_metadata = processor.get_file_date(test_file)
    if file_date:
        print(f"   ✓ Date extracted: {file_date}")
        print(f"   Has metadata: {has_metadata}")
    else:
        print(f"   ✗ No date found")
        print(f"   Has metadata: {has_metadata}")
    
    print("\n3. EXTRACTING GPS LOCATION:")
    print("-" * 40)
    location, city = processor.get_location_and_city(test_file)
    if location:
        print(f"   ✓ Location: {location}")
        print(f"   ✓ City: {city}")
    else:
        print(f"   ✗ No GPS data found")
        print(f"   Location: '{location}'")
        print(f"   City: '{city}'")
    
    print("\n4. TESTING FILENAME GENERATION:")
    print("-" * 40)
    from filename_generator import FilenameGenerator
    from datetime import datetime
    
    gen = FilenameGenerator("%Y.%m.%d-%H.%M.%S.{increment:03d}.{city}.{ext}")
    
    if file_date and has_metadata:
        new_name, _ = gen.generate_filename(
            test_file, file_date, has_metadata, location, city, 1
        )
        print(f"   Generated filename: {new_name}")
    else:
        print(f"   Cannot generate filename - no metadata")
    
    print("\n5. CHECKING FFPROBE AVAILABILITY:")
    print("-" * 40)
    import subprocess
    
    # Check for ffprobe
    ffprobe_found = False
    ffprobe_paths = [
        os.path.join(os.path.dirname(__file__), 'ffprobe.exe'),
        'ffprobe'
    ]
    
    for ffprobe_path in ffprobe_paths:
        try:
            result = subprocess.run([ffprobe_path, '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"   ✓ ffprobe found: {ffprobe_path}")
                ffprobe_found = True
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    
    if not ffprobe_found:
        print(f"   ✗ ffprobe not found")
        print(f"   Note: Video metadata extraction requires ffprobe")
        print(f"   Install ffmpeg to enable video metadata extraction")
    
    # If ffprobe is available, try to extract metadata directly
    if ffprobe_found:
        print("\n6. DETAILED FFPROBE METADATA:")
        print("-" * 40)
        try:
            # Get all metadata
            result = subprocess.run([
                ffprobe_path, '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                test_file
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                import json
                metadata = json.loads(result.stdout)
                
                # Show format tags
                if 'format' in metadata and 'tags' in metadata['format']:
                    print("   Format tags:")
                    for key, value in metadata['format']['tags'].items():
                        print(f"     {key}: {value}")
                else:
                    print("   No format tags found")
                
                # Show stream info
                if 'streams' in metadata:
                    print(f"\n   Streams: {len(metadata['streams'])}")
                    for i, stream in enumerate(metadata['streams']):
                        print(f"     Stream {i}: {stream.get('codec_type', 'unknown')}")
            else:
                print(f"   ffprobe error: {result.stderr}")
        except Exception as e:
            print(f"   Error running ffprobe: {e}")
    
    # Clean up
    if os.path.exists("test_cache.json"):
        os.remove("test_cache.json")
    
    print("\n" + "=" * 60)
    print("🔍 TEST COMPLETE")

if __name__ == "__main__":
    test_iphone_mov()