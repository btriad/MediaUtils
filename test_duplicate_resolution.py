"""
Unit tests for duplicate filename resolution functionality.

Tests the duplicate detection logic and sequential numbering system
that ensures no files are skipped due to naming conflicts.
"""

import unittest
import os
import tempfile
import shutil
from datetime import datetime
from typing import List, Tuple

from filename_generator import FilenameGenerator
from file_operations import FileOperations, FileInfo


class TestDuplicateResolution(unittest.TestCase):
    """Test cases for duplicate filename resolution."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = FilenameGenerator()
        self.file_ops = FileOperations({'.jpg', '.mp4', '.png'})
        self.test_dir = tempfile.mkdtemp()
        
        # Sample test data
        self.sample_date = datetime(2024, 6, 15, 14, 30, 45)
        self.sample_city = "TestCity"
        self.sample_location = "40.7128,-74.0060"
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_sequential_numbering_logic(self):
        """Test that duplicate names get sequential numbers (_001, _002, etc.)."""
        # Create a duplicate resolver instance
        from file_operations import DuplicateResolver
        resolver = DuplicateResolver()
        
        # Test data: multiple files that would generate the same name
        file_mappings = [
            ("IMG_001.jpg", "2024.06.15-14.30.45.001.jpg"),
            ("IMG_002.jpg", "2024.06.15-14.30.45.001.jpg"),  # Same as first
            ("IMG_003.jpg", "2024.06.15-14.30.45.001.jpg"),  # Same as first
            ("IMG_004.jpg", "2024.06.15-14.30.45.002.jpg"),  # Different base
        ]
        
        resolved_mappings = resolver.resolve_duplicates(file_mappings)
        
        # Check that duplicates are resolved with sequential numbering
        expected_results = [
            ("IMG_001.jpg", "2024.06.15-14.30.45.001.jpg"),
            ("IMG_002.jpg", "2024.06.15-14.30.45.001_001.jpg"),
            ("IMG_003.jpg", "2024.06.15-14.30.45.001_002.jpg"),
            ("IMG_004.jpg", "2024.06.15-14.30.45.002.jpg"),
        ]
        
        self.assertEqual(resolved_mappings, expected_results)
    
    def test_duplicate_detection_across_multiple_files(self):
        """Test duplicate detection works correctly across multiple files."""
        from file_operations import DuplicateResolver
        resolver = DuplicateResolver()
        
        # Test with various duplicate scenarios
        file_mappings = [
            ("file1.jpg", "same_name.jpg"),
            ("file2.jpg", "unique_name.jpg"),
            ("file3.jpg", "same_name.jpg"),  # Duplicate of file1
            ("file4.jpg", "another_same.jpg"),
            ("file5.jpg", "same_name.jpg"),  # Another duplicate
            ("file6.jpg", "another_same.jpg"),  # Duplicate of file4
        ]
        
        resolved_mappings = resolver.resolve_duplicates(file_mappings)
        
        # Verify all names are unique
        new_names = [mapping[1] for mapping in resolved_mappings]
        self.assertEqual(len(new_names), len(set(new_names)), 
                        "All resolved names should be unique")
        
        # Verify specific expected results
        expected_same_name_variants = [
            "same_name.jpg",
            "same_name_001.jpg", 
            "same_name_002.jpg"
        ]
        
        same_name_results = [name for _, name in resolved_mappings if "same_name" in name]
        self.assertEqual(sorted(same_name_results), sorted(expected_same_name_variants))
    
    def test_generate_unique_name_with_existing_names(self):
        """Test unique name generation when names already exist."""
        from file_operations import DuplicateResolver
        resolver = DuplicateResolver()
        
        existing_names = {
            "test.jpg",
            "test_001.jpg",
            "test_002.jpg"
        }
        
        unique_name = resolver.generate_unique_name("test.jpg", existing_names)
        self.assertEqual(unique_name, "test_003.jpg")
        
        # Test with no existing conflicts
        unique_name = resolver.generate_unique_name("unique.jpg", existing_names)
        self.assertEqual(unique_name, "unique.jpg")
    
    def test_conflict_resolution_with_existing_files(self):
        """Test conflict resolution when target files already exist on disk."""
        from file_operations import ConflictResolver
        resolver = ConflictResolver()
        
        # Create some existing files in test directory
        existing_files = ["existing.jpg", "existing_c1.jpg"]
        for filename in existing_files:
            with open(os.path.join(self.test_dir, filename), 'w') as f:
                f.write("test")
        
        # Test conflict resolution
        resolved_name = resolver.resolve_file_conflicts(self.test_dir, "existing.jpg")
        self.assertEqual(resolved_name, "existing_c2.jpg")
        
        # Test with no conflicts
        resolved_name = resolver.resolve_file_conflicts(self.test_dir, "no_conflict.jpg")
        self.assertEqual(resolved_name, "no_conflict.jpg")
    
    def test_integration_with_filename_generator(self):
        """Test duplicate resolution integration with filename generator."""
        # This test verifies that the filename generator can work with
        # the duplicate resolver to handle multiple files with same metadata
        
        files_data = [
            ("IMG_001.jpg", self.sample_date, True, self.sample_location, self.sample_city, 1),
            ("IMG_002.jpg", self.sample_date, True, self.sample_location, self.sample_city, 1),  # Same increment
            ("IMG_003.jpg", self.sample_date, True, self.sample_location, self.sample_city, 1),  # Same increment
        ]
        
        # Generate filenames
        generated_names = []
        for filepath, date, has_meta, location, city, increment in files_data:
            name, _ = self.generator.generate_filename(filepath, date, has_meta, location, city, increment)
            generated_names.append((os.path.basename(filepath), name))
        
        # Apply duplicate resolution
        from file_operations import DuplicateResolver
        resolver = DuplicateResolver()
        resolved_names = resolver.resolve_duplicates(generated_names)
        
        # Verify all names are unique
        final_names = [name for _, name in resolved_names]
        self.assertEqual(len(final_names), len(set(final_names)))
        
        # Verify first file keeps original name, others get suffixes
        self.assertTrue(resolved_names[0][1].endswith(".jpg"))
        self.assertTrue(resolved_names[1][1].endswith("_001.jpg"))
        self.assertTrue(resolved_names[2][1].endswith("_002.jpg"))
    
    def test_empty_and_edge_cases(self):
        """Test edge cases like empty lists and single files."""
        from file_operations import DuplicateResolver
        resolver = DuplicateResolver()
        
        # Empty list
        result = resolver.resolve_duplicates([])
        self.assertEqual(result, [])
        
        # Single file
        single_file = [("test.jpg", "new_name.jpg")]
        result = resolver.resolve_duplicates(single_file)
        self.assertEqual(result, single_file)
        
        # Files with "No metadata" or "Error" names should be skipped
        mixed_files = [
            ("file1.jpg", "valid_name.jpg"),
            ("file2.jpg", "No metadata"),
            ("file3.jpg", "Error: some error"),
            ("file4.jpg", "valid_name.jpg"),  # Duplicate of file1
        ]
        
        result = resolver.resolve_duplicates(mixed_files)
        
        # Should only resolve the valid names
        expected = [
            ("file1.jpg", "valid_name.jpg"),
            ("file2.jpg", "No metadata"),
            ("file3.jpg", "Error: some error"),
            ("file4.jpg", "valid_name_001.jpg"),
        ]
        
        self.assertEqual(result, expected)
    
    def test_preserve_file_extensions(self):
        """Test that file extensions are preserved in duplicate resolution."""
        from file_operations import DuplicateResolver
        resolver = DuplicateResolver()
        
        file_mappings = [
            ("img1.jpg", "photo.jpg"),
            ("vid1.mp4", "photo.mp4"),  # Different extension, no conflict
            ("img2.jpg", "photo.jpg"),  # Same extension, should conflict
        ]
        
        resolved = resolver.resolve_duplicates(file_mappings)
        
        # Verify extensions are preserved
        self.assertTrue(resolved[0][1].endswith(".jpg"))
        self.assertTrue(resolved[1][1].endswith(".mp4"))
        self.assertTrue(resolved[2][1].endswith(".jpg"))
        
        # Verify the jpg files have different names
        jpg_names = [name for _, name in resolved if name.endswith(".jpg")]
        self.assertEqual(len(jpg_names), 2)
        self.assertNotEqual(jpg_names[0], jpg_names[1])


if __name__ == '__main__':
    unittest.main()