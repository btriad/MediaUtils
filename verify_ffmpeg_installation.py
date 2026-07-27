#!/usr/bin/env python3
"""
Verify FFmpeg installation and test MOV file support.
"""

import subprocess
import os
import sys

print("🔍 VERIFYING FFMPEG INSTALLATION")
print("=" * 60)

# Check if ffprobe is available
print("\n1. Checking for ffprobe...")
ffprobe_found = False
ffprobe_path = None

# Try different locations
locations = [
    'ffprobe',  # System PATH
    os.path.join(os.path.dirname(__file__), 'ffprobe.exe'),  # Local
    r'C:\ffmpeg\bin\ffprobe.exe',  # Common manual install location
]

for location in locations:
    try:
        result = subprocess.run([location, '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"   ✅ ffprobe found: {location}")
            ffprobe_found = True
            ffprobe_path = location
            
            # Show version
            version_line = result.stdout.split('\n')[0]
            print(f"   Version: {version_line}")
            break
    except (FileNotFoundError, subprocess.TimeoutExpired):
        continue
    except Exception as e:
        print(f"   Error checking {location}: {e}")

if not ffprobe_found:
    print("   ❌ ffprobe NOT found")
    print("\n⚠️  FFmpeg was installed but not found in PATH")
    print("\n📋 NEXT STEPS:")
    print("   1. Close this terminal/PowerShell window")
    print("   2. Open a NEW terminal/PowerShell window")
    print("   3. Run this script again: python verify_ffmpeg_installation.py")
    print("\n   OR restart Kiro IDE to refresh the PATH")
    sys.exit(1)

# Test with actual MOV file if available
print("\n2. Testing with test.MOV file...")
if os.path.exists("test.MOV"):
    print("   ✅ test.MOV found")
    
    # Try to extract metadata
    try:
        result = subprocess.run([
            ffprobe_path, '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            'test.MOV'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            import json
            metadata = json.loads(result.stdout)
            
            print("   ✅ Metadata extraction successful!")
            
            # Show some metadata
            if 'format' in metadata:
                fmt = metadata['format']
                if 'tags' in fmt:
                    print(f"\n   📋 Available metadata:")
                    for key, value in list(fmt['tags'].items())[:5]:
                        print(f"      {key}: {value}")
                
                if 'duration' in fmt:
                    duration = float(fmt['duration'])
                    print(f"      duration: {duration:.2f} seconds")
            
            if 'streams' in metadata:
                print(f"      streams: {len(metadata['streams'])}")
        else:
            print(f"   ⚠️  ffprobe error: {result.stderr}")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
else:
    print("   ⚠️  test.MOV not found (skipping metadata test)")

# Test with the application
print("\n3. Testing with Media File Renamer...")
try:
    from media_processor import MediaProcessor
    processor = MediaProcessor()
    
    if os.path.exists("test.MOV"):
        file_date, has_metadata = processor.get_file_date("test.MOV")
        location, city = processor.get_location_and_city("test.MOV")
        
        print(f"   Date extracted: {file_date if file_date else 'None'}")
        print(f"   Has metadata: {has_metadata}")
        print(f"   Location: {location if location else 'None'}")
        print(f"   City: {city if city else 'None'}")
        
        if has_metadata:
            print("\n   ✅ MOV file support is WORKING!")
        else:
            print("\n   ⚠️  No metadata found (file may not contain metadata)")
    else:
        print("   ⚠️  test.MOV not found (skipping application test)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
if ffprobe_found:
    print("✅ FFmpeg is installed and working!")
    print("\n📋 NEXT STEPS:")
    print("   1. Run the application: python main.py")
    print("   2. Select a folder with MOV files")
    print("   3. Click 'Show Files' - MOV files should now show metadata")
else:
    print("❌ FFmpeg installation needs attention")
    print("   Please restart your terminal and try again")
