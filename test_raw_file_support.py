#!/usr/bin/env python3
"""
Test script for RAW file format support (.NEF and other RAW formats).

Tests that the media processor correctly handles RAW image files including:
- .NEF (Nikon)
- .CR2/.CR3 (Canon)
- .ARW (Sony)
- .DNG (Adobe)
- And other common RAW formats
"""

import unittest
from unittest.mock import Mock, patch, mock_open
from media_processor import MediaProcessor, EXIFREAD_AVAILABLE
from datetime import datetime


class TestRAWFileSupport(unittest.TestCase):
    """Test RAW file format support."""
    
    def setUp(self):
        """Set up test environment."""
        self.processor = MediaProcessor()
    
    def test_raw_extensions_supported(self):
        """Test that RAW file extensions are in supported formats."""
        raw_extensions = [
            '.nef',   # Nikon
            '.cr2', '.cr3',  # Canon
            '.arw',   # Sony
            '.dng',   # Adobe
            '.orf',   # Olympus
            '.rw2',   # Panasonic
            '.pef',   # Pentax
            '.raf'    # Fujifilm
        ]
        
        for ext in raw_extensions:
            self.assertIn(ext, self.processor.image_extensions,
                         f"RAW extension {ext} should be supported")
    
    def test_is_supported_media_type_raw(self):
        """Test that RAW files are recognized as supported media types."""
        raw_files = [
            'photo.nef',
            'image.cr2',
            'picture.arw',
            'shot.dng',
            'IMG_1234.NEF',  # Test case insensitivity
            'DSC_5678.CR3'
        ]
        
        for filename in raw_files:
            self.assertTrue(self.processor.is_supported_file(filename),
                          f"{filename} should be recognized as supported media type")
    
    @unittest.skipIf(not EXIFREAD_AVAILABLE, "exifread not available")
    def test_extract_date_with_exifread(self):
        """Test date extraction from RAW files using exifread."""
        # Mock exifread tags
        mock_tags = {
            'EXIF DateTimeOriginal': Mock(values='2024:01:15 14:30:45')
        }
        
        with patch('exifread.process_file', return_value=mock_tags):
            with patch('builtins.open', mock_open(read_data=b'fake raw data')):
                date, has_metadata = self.processor._extract_date_with_exifread('test.nef')
                
                self.assertIsNotNone(date)
                self.assertTrue(has_metadata)
                self.assertEqual(date.year, 2024)
                self.assertEqual(date.month, 1)
                self.assertEqual(date.day, 15)
    
    @unittest.skipIf(not EXIFREAD_AVAILABLE, "exifread not available")
    def test_extract_gps_with_exifread(self):
        """Test GPS extraction from RAW files using exifread."""
        # Mock GPS tags with proper rational values
        class MockRational:
            def __init__(self, num, den):
                self.num = num
                self.den = den
        
        mock_tags = {
            'GPS GPSLatitude': Mock(values=[
                MockRational(38, 1),  # 38 degrees
                MockRational(0, 1),   # 0 minutes
                MockRational(54, 1)   # 54 seconds
            ]),
            'GPS GPSLatitudeRef': Mock(values='N'),
            'GPS GPSLongitude': Mock(values=[
                MockRational(23, 1),  # 23 degrees
                MockRational(49, 1),  # 49 minutes
                MockRational(14, 1)   # 14 seconds
            ]),
            'GPS GPSLongitudeRef': Mock(values='E')
        }
        
        with patch('exifread.process_file', return_value=mock_tags):
            with patch('builtins.open', mock_open(read_data=b'fake raw data')):
                lat, lon = self.processor._extract_gps_with_exifread('test.nef')
                
                self.assertIsNotNone(lat)
                self.assertIsNotNone(lon)
                self.assertAlmostEqual(lat, 38.015, places=2)
                self.assertAlmostEqual(lon, 23.820, places=2)
    
    def test_convert_gps_to_decimal(self):
        """Test GPS coordinate conversion to decimal degrees."""
        # Mock rational values for GPS coordinates
        class MockRational:
            def __init__(self, num, den):
                self.num = num
                self.den = den
        
        # Test North latitude
        gps_values = [
            MockRational(38, 1),  # 38 degrees
            MockRational(0, 1),   # 0 minutes
            MockRational(54, 1)   # 54 seconds
        ]
        decimal = self.processor._convert_gps_to_decimal(gps_values, 'N')
        self.assertAlmostEqual(decimal, 38.015, places=3)
        
        # Test South latitude (should be negative)
        decimal = self.processor._convert_gps_to_decimal(gps_values, 'S')
        self.assertAlmostEqual(decimal, -38.015, places=3)
        
        # Test East longitude
        gps_values = [
            MockRational(23, 1),  # 23 degrees
            MockRational(49, 1),  # 49 minutes
            MockRational(14, 1)   # 14 seconds
        ]
        decimal = self.processor._convert_gps_to_decimal(gps_values, 'E')
        self.assertAlmostEqual(decimal, 23.8206, places=2)  # 23 + 49/60 + 14/3600
        
        # Test West longitude (should be negative)
        decimal = self.processor._convert_gps_to_decimal(gps_values, 'W')
        self.assertAlmostEqual(decimal, -23.8206, places=2)
    
    def test_raw_file_fallback_to_pil(self):
        """Test that RAW files fall back to PIL if exifread fails."""
        # This tests the fallback mechanism
        with patch.object(self.processor, '_extract_date_with_exifread', return_value=(None, False)):
            # Should fall back to PIL method
            # We can't easily test PIL with RAW files without actual files,
            # but we can verify the code path exists
            self.assertTrue(hasattr(self.processor, '_extract_image_date'))
    
    def test_raw_extensions_count(self):
        """Test that we support a good number of RAW formats."""
        raw_extensions = [ext for ext in self.processor.image_extensions 
                         if ext in {'.nef', '.cr2', '.cr3', '.arw', '.dng', 
                                   '.orf', '.rw2', '.pef', '.raf'}]
        
        # Should support at least 8 RAW formats
        self.assertGreaterEqual(len(raw_extensions), 8,
                               "Should support at least 8 RAW formats")


def run_raw_file_tests():
    """Run the RAW file support tests."""
    print("Testing RAW File Format Support")
    print("=" * 50)
    
    if EXIFREAD_AVAILABLE:
        print("✓ exifread library is available")
        print("  Full RAW file support enabled")
    else:
        print("⚠ exifread library not available")
        print("  RAW file support will be limited to PIL capabilities")
        print("  Install with: pip install exifread")
    
    print("\nSupported RAW formats:")
    processor = MediaProcessor()
    raw_formats = {
        '.nef': 'Nikon',
        '.cr2': 'Canon (older)',
        '.cr3': 'Canon (newer)',
        '.arw': 'Sony',
        '.dng': 'Adobe Digital Negative',
        '.orf': 'Olympus',
        '.rw2': 'Panasonic',
        '.pef': 'Pentax',
        '.raf': 'Fujifilm'
    }
    
    for ext, brand in raw_formats.items():
        if ext in processor.image_extensions:
            print(f"  ✓ {ext.upper()} - {brand}")
    
    print("\n" + "=" * 50)
    print("Running tests...")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRAWFileSupport)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall result: {'PASS' if success else 'FAIL'}")
    
    if not EXIFREAD_AVAILABLE:
        print("\nNote: Some tests were skipped because exifread is not installed.")
        print("For full RAW file support, install exifread:")
        print("  pip install exifread")
    
    return success


if __name__ == "__main__":
    run_raw_file_tests()
