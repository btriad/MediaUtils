#!/usr/bin/env python3
"""
Demo script to showcase RAW file format support.

Demonstrates that the application now supports:
- .NEF (Nikon RAW)
- .CR2/.CR3 (Canon RAW)
- .ARW (Sony RAW)
- .DNG (Adobe Digital Negative)
- And other common RAW formats
"""

from media_processor import MediaProcessor, EXIFREAD_AVAILABLE


def demo_raw_file_support():
    """Demonstrate RAW file format support."""
    print("=" * 60)
    print("RAW FILE FORMAT SUPPORT DEMONSTRATION")
    print("=" * 60)
    
    # Create media processor
    processor = MediaProcessor()
    
    # Check exifread availability
    print("\n1. EXIFREAD LIBRARY STATUS")
    print("-" * 60)
    if EXIFREAD_AVAILABLE:
        print("✓ exifread is installed")
        print("  Full RAW file support is enabled")
        print("  All RAW formats will have complete metadata extraction")
    else:
        print("⚠ exifread is NOT installed")
        print("  RAW file support is limited to PIL capabilities")
        print("  Some RAW formats may not work properly")
        print("\n  To enable full RAW support, install exifread:")
        print("  pip install exifread")
    
    # Display supported RAW formats
    print("\n2. SUPPORTED RAW FORMATS")
    print("-" * 60)
    
    raw_formats = {
        '.nef': ('Nikon', 'Nikon Electronic Format'),
        '.cr2': ('Canon', 'Canon RAW 2 (older models)'),
        '.cr3': ('Canon', 'Canon RAW 3 (newer models)'),
        '.arw': ('Sony', 'Sony Alpha RAW'),
        '.dng': ('Adobe', 'Digital Negative (universal)'),
        '.orf': ('Olympus', 'Olympus RAW Format'),
        '.rw2': ('Panasonic', 'Panasonic RAW 2'),
        '.pef': ('Pentax', 'Pentax Electronic File'),
        '.raf': ('Fujifilm', 'RAW File Format')
    }
    
    for ext, (brand, description) in raw_formats.items():
        if ext in processor.image_extensions:
            print(f"✓ {ext.upper():6} - {brand:12} - {description}")
        else:
            print(f"✗ {ext.upper():6} - {brand:12} - NOT SUPPORTED")
    
    # Test file recognition
    print("\n3. FILE RECOGNITION TEST")
    print("-" * 60)
    
    test_files = [
        ('DSC_1234.NEF', 'Nikon RAW'),
        ('IMG_5678.CR2', 'Canon RAW (old)'),
        ('IMG_9012.CR3', 'Canon RAW (new)'),
        ('DSC00345.ARW', 'Sony RAW'),
        ('photo.DNG', 'Adobe DNG'),
        ('P1234567.ORF', 'Olympus RAW'),
        ('P1000123.RW2', 'Panasonic RAW'),
        ('IMGP0001.PEF', 'Pentax RAW'),
        ('DSCF1234.RAF', 'Fujifilm RAW'),
        ('IMG_1234.JPG', 'JPEG (for comparison)')
    ]
    
    for filename, description in test_files:
        is_supported = processor.is_supported_file(filename)
        status = "✓ SUPPORTED" if is_supported else "✗ NOT SUPPORTED"
        print(f"{status:15} - {filename:20} ({description})")
    
    # Display total supported formats
    print("\n4. SUMMARY")
    print("-" * 60)
    
    total_image_formats = len(processor.image_extensions)
    raw_formats_count = len([ext for ext in processor.image_extensions 
                            if ext in {'.nef', '.cr2', '.cr3', '.arw', '.dng', 
                                      '.orf', '.rw2', '.pef', '.raf'}])
    standard_formats_count = total_image_formats - raw_formats_count
    
    print(f"Total image formats supported: {total_image_formats}")
    print(f"  - Standard formats (JPEG, PNG, etc.): {standard_formats_count}")
    print(f"  - RAW formats: {raw_formats_count}")
    print(f"Total video formats supported: {len(processor.video_extensions)}")
    
    # Feature overview
    print("\n5. RAW FILE FEATURES")
    print("-" * 60)
    print("✓ Date/time extraction from EXIF data")
    print("✓ GPS coordinate extraction")
    print("✓ City name lookup from GPS coordinates")
    print("✓ Automatic fallback to file modification date")
    print("✓ Error recovery for corrupted files")
    print("✓ Batch processing support")
    print("✓ Cache optimization for GPS lookups")
    
    # Usage instructions
    print("\n6. USAGE")
    print("-" * 60)
    print("RAW files are processed automatically:")
    print("1. Select a folder containing RAW files")
    print("2. Click 'Show Files' to scan for media")
    print("3. RAW files appear in the list with metadata")
    print("4. Process files normally to rename them")
    
    # Recommendations
    print("\n7. RECOMMENDATIONS")
    print("-" * 60)
    if not EXIFREAD_AVAILABLE:
        print("⚠ IMPORTANT: Install exifread for full RAW support")
        print("  Command: pip install exifread")
        print("")
    print("✓ Test with a few files before batch processing")
    print("✓ Keep backups of original files")
    print("✓ Check the preview before processing")
    print("✓ Review the application log for any issues")
    
    print("\n" + "=" * 60)
    print("RAW FILE SUPPORT DEMONSTRATION COMPLETE")
    print("=" * 60)
    
    if EXIFREAD_AVAILABLE:
        print("\n✓ Your system is ready for full RAW file processing!")
    else:
        print("\n⚠ Install exifread for optimal RAW file support")
        print("  pip install exifread")


if __name__ == "__main__":
    demo_raw_file_support()
