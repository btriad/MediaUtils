"""
Final verification test for duplicate resolution implementation.

Verifies that all requirements are met according to the specification.
"""

import unittest
import os
import tempfile
import shutil
from datetime import datetime

from filename_generator import FilenameGenerator
from file_operations import FileOperations, FileInfo


class TestFinalVerification(unittest.TestCase):
    """Final verification tests for all requirements."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = FilenameGenerator()
        self.file_ops = FileOperations({'.jpg', '.mp4', '.png'})
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_requirement_1_1_sequential_numbers_for_duplicates(self):
        """Requirement 1.1: Multiple files with same name get sequential numbers."""
        file_mappings = [
            ("file1.jpg", "same_name.jpg"),
            ("file2.jpg", "same_name.jpg"),
            ("file3.jpg", "same_name.jpg"),
        ]
        
        resolved = self.file_ops.duplicate_resolver.resolve_duplicates(file_mappings)
        
        expected = [
            ("file1.jpg", "same_name.jpg"),
            ("file2.jpg", "same_name_001.jpg"),
            ("file3.jpg", "same_name_002.jpg"),
        ]
        
        self.assertEqual(resolved, expected)
    
    def test_requirement_1_2_first_duplicate_gets_001(self):
        """Requirement 1.2: First duplicate gets _001 suffix."""
        file_mappings = [
            ("original.jpg", "name.jpg"),
            ("duplicate.jpg", "name.jpg"),
        ]
        
        resolved = self.file_ops.duplicate_resolver.resolve_duplicates(file_mappings)
        
        # First occurrence keeps original name, first duplicate gets _001
        self.assertEqual(resolved[0][1], "name.jpg")
        self.assertEqual(resolved[1][1], "name_001.jpg")
    
    def test_requirement_1_3_subsequent_duplicates_increment(self):
        """Requirement 1.3: Subsequent duplicates increment (_002, _003, etc.)."""
        file_mappings = [
            ("file1.jpg", "test.jpg"),
            ("file2.jpg", "test.jpg"),
            ("file3.jpg", "test.jpg"),
            ("file4.jpg", "test.jpg"),
        ]
        
        resolved = self.file_ops.duplicate_resolver.resolve_duplicates(file_mappings)
        
        expected_names = ["test.jpg", "test_001.jpg", "test_002.jpg", "test_003.jpg"]
        actual_names = [name for _, name in resolved]
        
        self.assertEqual(actual_names, expected_names)
    
    def test_requirement_1_4_consider_existing_files(self):
        """Requirement 1.4: Check both generated names and existing files."""
        # Create existing file
        existing_file = os.path.join(self.test_dir, "existing.jpg")
        with open(existing_file, 'w') as f:
            f.write("test")
        
        # Test conflict resolution
        resolved_name = self.file_ops.conflict_resolver.resolve_file_conflicts(
            self.test_dir, "existing.jpg"
        )
        
        # Should get conflict suffix since file exists
        self.assertEqual(resolved_name, "existing_c1.jpg")
    
    def test_requirement_1_5_display_final_names(self):
        """Requirement 1.5: System shows final unique names."""
        # This is tested through the FileInfo final_name field
        file_infos = [
            FileInfo(
                original_name="img1.jpg",
                original_path="/path/img1.jpg",
                new_name="photo.jpg",
                final_name="photo.jpg",
                location="",
                city="",
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="img2.jpg",
                original_path="/path/img2.jpg",
                new_name="photo.jpg",
                final_name="photo.jpg",
                location="",
                city="",
                has_metadata=True,
                selected=True
            )
        ]
        
        resolved_infos = self.file_ops.resolve_duplicates_and_conflicts(
            self.test_dir, file_infos
        )
        
        # Verify final_name field is populated with unique names
        final_names = [info.final_name for info in resolved_infos]
        self.assertEqual(len(final_names), len(set(final_names)))
        self.assertEqual(final_names[0], "photo.jpg")
        self.assertEqual(final_names[1], "photo_001.jpg")
    
    def test_integration_with_filename_generator_batch(self):
        """Test integration with filename generator batch processing."""
        # Test data for batch generation
        file_data = [
            ("IMG_001.jpg", datetime(2024, 6, 15, 14, 30, 45), True, "40.7128,-74.0060", "NYC", 1),
            ("IMG_002.jpg", datetime(2024, 6, 15, 14, 30, 45), True, "40.7128,-74.0060", "NYC", 1),
            ("IMG_003.jpg", datetime(2024, 6, 15, 14, 30, 45), True, "40.7128,-74.0060", "NYC", 1),
        ]
        
        # Generate batch filenames with duplicate resolution
        result = self.generator.generate_batch_filenames(file_data, resolve_duplicates=True)
        
        # All names should be unique
        names = [name for _, name in result]
        self.assertEqual(len(names), len(set(names)))
        
        # Should have proper suffixes
        self.assertTrue(names[0].endswith(".jpg"))
        self.assertTrue(names[1].endswith("_001.jpg"))
        self.assertTrue(names[2].endswith("_002.jpg"))


if __name__ == '__main__':
    unittest.main()