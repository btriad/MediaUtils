#!/usr/bin/env python3
"""
Test XMP sidecar file support.

Tests:
1. XMP file detection
2. GPS extraction from XMP
3. Date extraction from XMP
4. XMP renaming alongside image files
"""

import unittest
import os
import tempfile
import shutil
from xmp_handler import XMPHandler
from media_processor import MediaProcessor
from file_operations import FileOperations


class TestXMPSupport(unittest.TestCase):
    """Test XMP sidecar file support."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix="xmp_test_")
        self.xmp_handler = XMPHandler()
    
    def tearDown(self):
        """Clean up test environment."""
        try:
            shutil.rmtree(self.test_dir)
        except:
            pass
    
    def create_test_xmp(self, filename, lat=None, lon=None, date=None):
        """Create a test XMP file with optional GPS and date."""
        xmp_content = '''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""
        xmlns:exif="http://ns.adobe.com/exif/1.0/"
        xmlns:xmp="http://ns.adobe.com/xap/1.0/">
'''
        
        if lat is not None and lon is not None:
            xmp_content += f'''      <exif:GPSLatitude>{lat}</exif:GPSLatitude>
      <exif:GPSLongitude>{lon}</exif:GPSLongitude>
'''
        
        if date:
            xmp_content += f'''      <exif:DateTimeOriginal>{date}</exif:DateTimeOriginal>
'''
        
        xmp_content += '''    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>'''
        
        xmp_path = os.path.join(self.test_dir, filename)
        with open(xmp_path, 'w', encoding='utf-8') as f:
            f.write(xmp_content)
        
        return xmp_path
    
    def test_find_xmp_file(self):
        """Test XMP file detection."""
        # Create test image and XMP
        image_path = os.path.join(self.test_dir, "test.nef")
        xmp_path = os.path.join(self.test_dir, "test.xmp")
        
        open(image_path, 'w').close()
        open(xmp_path, 'w').close()
        
        # Test finding XMP
        found_xmp = self.xmp_handler.find_xmp_file(image_path)
        self.assertEqual(found_xmp, xmp_path)
        print("✓ XMP file detection works")
    
    def test_extract_gps_from_xmp(self):
        """Test GPS extraction from XMP."""
        # Create XMP with GPS data (Athens, Greece)
        xmp_path = self.create_test_xmp("test.xmp", lat="38.015", lon="23.8206")
        
        # Extract GPS
        lat, lon = self.xmp_handler.extract_gps_from_xmp(xmp_path)
        
        self.assertIsNotNone(lat)
        self.assertIsNotNone(lon)
        self.assertAlmostEqual(lat, 38.015, places=3)
        self.assertAlmostEqual(lon, 23.8206, places=3)
        print(f"✓ GPS extraction from XMP works: {lat:.6f}, {lon:.6f}")
    
    def test_extract_date_from_xmp(self):
        """Test date extraction from XMP."""
        # Create XMP with date
        xmp_path = self.create_test_xmp("test.xmp", date="2024-03-14T11:56:10")
        
        # Extract date
        date = self.xmp_handler.extract_date_from_xmp(xmp_path)
        
        self.assertIsNotNone(date)
        self.assertEqual(date.year, 2024)
        self.assertEqual(date.month, 3)
        self.assertEqual(date.day, 14)
        print(f"✓ Date extraction from XMP works: {date}")
    
    def test_rename_xmp_with_image(self):
        """Test XMP renaming alongside image."""
        # Create test files
        old_image = os.path.join(self.test_dir, "old_name.nef")
        old_xmp = os.path.join(self.test_dir, "old_name.xmp")
        new_image = os.path.join(self.test_dir, "new_name.nef")
        new_xmp = os.path.join(self.test_dir, "new_name.xmp")
        
        open(old_image, 'w').close()
        open(old_xmp, 'w').close()
        
        # Rename XMP
        success = self.xmp_handler.rename_xmp_with_image(old_image, new_image)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(new_xmp))
        self.assertFalse(os.path.exists(old_xmp))
        print("✓ XMP renaming works")
    
    def test_media_processor_uses_xmp(self):
        """Test that MediaProcessor uses XMP data."""
        # Create NEF without GPS and XMP with GPS
        nef_path = os.path.join(self.test_dir, "test.nef")
        open(nef_path, 'wb').close()  # Empty NEF
        
        # Create XMP with GPS
        self.create_test_xmp("test.xmp", lat="38.015", lon="23.8206")
        
        # Process with MediaProcessor
        processor = MediaProcessor()
        location, city = processor.get_location_and_city(nef_path)
        
        # Should find GPS from XMP
        self.assertNotEqual(location, "No GPS")
        print(f"✓ MediaProcessor uses XMP GPS: {location}")


def run_xmp_tests():
    """Run XMP support tests."""
    print("=" * 70)
    print("TESTING XMP SIDECAR FILE SUPPORT")
    print("=" * 70)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestXMPSupport)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall result: {'PASS' if success else 'FAIL'}")
    
    if success:
        print("\n✓ XMP sidecar file support is working correctly!")
        print("\nFeatures:")
        print("  ✓ XMP file detection")
        print("  ✓ GPS extraction from XMP")
        print("  ✓ Date extraction from XMP")
        print("  ✓ XMP renaming alongside images")
        print("  ✓ MediaProcessor integration")
    
    return success


if __name__ == "__main__":
    run_xmp_tests()
