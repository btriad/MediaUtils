"""
Integration test for duplicate resolution functionality.

Tests the complete workflow from filename generation through duplicate resolution.
"""

import unittest
import os
import tempfile
import shutil
from datetime import datetime

from filename_generator import FilenameGenerator
from file_operations import FileOperations, FileInfo


class TestDuplicateIntegration(unittest.TestCase):
    """Integration tests for duplicate resolution workflow."""
    
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
    
    def test_complete_duplicate_resolution_workflow(self):
        """Test the complete workflow from FileInfo creation to duplicate resolution."""
        # Create test FileInfo objects that would generate duplicate names
        file_infos = [
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(self.test_dir, "IMG_001.jpg"),
                new_name="2024.06.15-14.30.45.001.jpg",
                final_name="2024.06.15-14.30.45.001.jpg",
                location=self.sample_location,
                city=self.sample_city,
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="IMG_002.jpg",
                original_path=os.path.join(self.test_dir, "IMG_002.jpg"),
                new_name="2024.06.15-14.30.45.001.jpg",  # Same as first
                final_name="2024.06.15-14.30.45.001.jpg",
                location=self.sample_location,
                city=self.sample_city,
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="IMG_003.jpg",
                original_path=os.path.join(self.test_dir, "IMG_003.jpg"),
                new_name="2024.06.15-14.30.45.001.jpg",  # Same as first
                final_name="2024.06.15-14.30.45.001.jpg",
                location=self.sample_location,
                city=self.sample_city,
                has_metadata=True,
                selected=True
            )
        ]
        
        # Apply duplicate resolution
        resolved_file_infos = self.file_ops.resolve_duplicates_and_conflicts(
            self.test_dir, file_infos
        )
        
        # Verify all final names are unique
        final_names = [info.final_name for info in resolved_file_infos]
        self.assertEqual(len(final_names), len(set(final_names)), 
                        "All final names should be unique")
        
        # Verify specific expected results
        expected_names = [
            "2024.06.15-14.30.45.001.jpg",
            "2024.06.15-14.30.45.001_001.jpg",
            "2024.06.15-14.30.45.001_002.jpg"
        ]
        
        self.assertEqual(sorted(final_names), sorted(expected_names))
    
    def test_conflict_resolution_with_existing_files(self):
        """Test conflict resolution when files already exist on disk."""
        # Create an existing file
        existing_file = os.path.join(self.test_dir, "2024.06.15-14.30.45.001.jpg")
        with open(existing_file, 'w') as f:
            f.write("existing file")
        
        # Create FileInfo that would conflict
        file_infos = [
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(self.test_dir, "IMG_001.jpg"),
                new_name="2024.06.15-14.30.45.001.jpg",
                final_name="2024.06.15-14.30.45.001.jpg",
                location=self.sample_location,
                city=self.sample_city,
                has_metadata=True,
                selected=True
            )
        ]
        
        # Apply resolution
        resolved_file_infos = self.file_ops.resolve_duplicates_and_conflicts(
            self.test_dir, file_infos
        )
        
        # Should resolve to conflict name
        self.assertEqual(resolved_file_infos[0].final_name, "2024.06.15-14.30.45.001_c1.jpg")
    
    def test_mixed_valid_and_invalid_names(self):
        """Test resolution with mix of valid names, errors, and no metadata."""
        file_infos = [
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(self.test_dir, "IMG_001.jpg"),
                new_name="valid_name.jpg",
                final_name="valid_name.jpg",
                location=self.sample_location,
                city=self.sample_city,
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="IMG_002.jpg",
                original_path=os.path.join(self.test_dir, "IMG_002.jpg"),
                new_name="No metadata",
                final_name="No metadata",
                location="",
                city="",
                has_metadata=False,
                selected=True
            ),
            FileInfo(
                original_name="IMG_003.jpg",
                original_path=os.path.join(self.test_dir, "IMG_003.jpg"),
                new_name="Error: some error",
                final_name="Error: some error",
                location="",
                city="",
                has_metadata=False,
                selected=True
            ),
            FileInfo(
                original_name="IMG_004.jpg",
                original_path=os.path.join(self.test_dir, "IMG_004.jpg"),
                new_name="valid_name.jpg",  # Duplicate of first
                final_name="valid_name.jpg",
                location=self.sample_location,
                city=self.sample_city,
                has_metadata=True,
                selected=True
            )
        ]
        
        # Apply resolution
        resolved_file_infos = self.file_ops.resolve_duplicates_and_conflicts(
            self.test_dir, file_infos
        )
        
        # Check results
        final_names = [info.final_name for info in resolved_file_infos]
        
        # Valid names should be resolved, invalid ones unchanged
        expected_names = [
            "valid_name.jpg",
            "No metadata",
            "Error: some error", 
            "valid_name_001.jpg"
        ]
        
        self.assertEqual(final_names, expected_names)


if __name__ == '__main__':
    unittest.main()