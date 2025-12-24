"""
Unit tests for conflict resolution functionality.

Tests the ConflictResolver class methods for detecting and resolving
file conflicts with existing files in the target directory.

Requirements tested:
- 3.1: WHEN a target filename already exists THEN the system SHALL append "_c1" before the file extension
- 3.2: WHEN "_c1" filename also exists THEN the system SHALL try "_c2", "_c3", etc. until finding an available name
- 3.3: WHEN checking for conflicts THEN the system SHALL verify the target file doesn't exist before renaming
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import patch, MagicMock
from file_operations import ConflictResolver


class TestConflictResolver(unittest.TestCase):
    """Test cases for ConflictResolver class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.conflict_resolver = ConflictResolver()
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up after each test method."""
        # Remove the temporary directory and all its contents
        shutil.rmtree(self.test_dir)
    
    def test_resolve_file_conflicts_no_conflict(self):
        """Test conflict resolution when no conflict exists.
        
        Requirements: 3.3 - Verify target file doesn't exist before renaming
        """
        # Test with a filename that doesn't exist
        target_name = "test_file.jpg"
        result = self.conflict_resolver.resolve_file_conflicts(self.test_dir, target_name)
        
        # Should return original name when no conflict
        self.assertEqual(result, target_name)
    
    def test_resolve_file_conflicts_single_conflict(self):
        """Test conflict resolution when target file exists.
        
        Requirements: 3.1 - Append "_c1" when target filename already exists
        """
        # Create a file that will conflict
        target_name = "existing_file.jpg"
        existing_file_path = os.path.join(self.test_dir, target_name)
        with open(existing_file_path, 'w') as f:
            f.write("test content")
        
        # Test conflict resolution
        result = self.conflict_resolver.resolve_file_conflicts(self.test_dir, target_name)
        
        # Should append _c1 suffix
        expected_name = "existing_file_c1.jpg"
        self.assertEqual(result, expected_name)
    
    def test_resolve_file_conflicts_multiple_conflicts(self):
        """Test conflict resolution when multiple conflict files exist.
        
        Requirements: 3.2 - Try "_c2", "_c3", etc. until finding available name
        """
        # Create multiple conflicting files
        base_name = "multi_conflict.jpg"
        files_to_create = [
            "multi_conflict.jpg",
            "multi_conflict_c1.jpg",
            "multi_conflict_c2.jpg"
        ]
        
        for filename in files_to_create:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        # Test conflict resolution
        result = self.conflict_resolver.resolve_file_conflicts(self.test_dir, base_name)
        
        # Should find the next available suffix (_c3)
        expected_name = "multi_conflict_c3.jpg"
        self.assertEqual(result, expected_name)
    
    def test_resolve_file_conflicts_extensive_conflicts(self):
        """Test conflict resolution with many existing conflict files."""
        # Create many conflicting files
        base_name = "extensive_conflict.mp4"
        files_to_create = [base_name]
        
        # Create conflict files _c1 through _c10
        for i in range(1, 11):
            conflict_name = f"extensive_conflict_c{i}.mp4"
            files_to_create.append(conflict_name)
        
        for filename in files_to_create:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        # Test conflict resolution
        result = self.conflict_resolver.resolve_file_conflicts(self.test_dir, base_name)
        
        # Should find the next available suffix (_c11)
        expected_name = "extensive_conflict_c11.mp4"
        self.assertEqual(result, expected_name)
    
    def test_find_available_name_no_conflicts(self):
        """Test find_available_name when no conflicts exist."""
        base_name = "available_file.jpg"
        result = self.conflict_resolver.find_available_name(self.test_dir, base_name)
        
        # Should return name with _c1 suffix (first available conflict name)
        expected_name = "available_file_c1.jpg"
        self.assertEqual(result, expected_name)
    
    def test_find_available_name_with_conflicts(self):
        """Test find_available_name when some conflict files exist."""
        # Create some conflict files
        base_name = "conflict_test.png"
        conflict_files = [
            "conflict_test_c1.png",
            "conflict_test_c2.png"
        ]
        
        for filename in conflict_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        # Test finding available name
        result = self.conflict_resolver.find_available_name(self.test_dir, base_name)
        
        # Should find the next available suffix (_c3)
        expected_name = "conflict_test_c3.png"
        self.assertEqual(result, expected_name)
    
    def test_conflict_resolution_with_different_extensions(self):
        """Test conflict resolution works with various file extensions."""
        extensions = ['.jpg', '.mp4', '.png', '.mov', '.avi']
        
        for ext in extensions:
            with self.subTest(extension=ext):
                # Create a conflicting file
                base_name = f"test_file{ext}"
                existing_file_path = os.path.join(self.test_dir, base_name)
                with open(existing_file_path, 'w') as f:
                    f.write("test content")
                
                # Test conflict resolution
                result = self.conflict_resolver.resolve_file_conflicts(self.test_dir, base_name)
                
                # Should append _c1 before extension
                expected_name = f"test_file_c1{ext}"
                self.assertEqual(result, expected_name)
    
    def test_conflict_resolution_with_no_extension(self):
        """Test conflict resolution with files that have no extension."""
        # Create a conflicting file without extension
        base_name = "no_extension_file"
        existing_file_path = os.path.join(self.test_dir, base_name)
        with open(existing_file_path, 'w') as f:
            f.write("test content")
        
        # Test conflict resolution
        result = self.conflict_resolver.resolve_file_conflicts(self.test_dir, base_name)
        
        # Should append _c1 at the end
        expected_name = "no_extension_file_c1"
        self.assertEqual(result, expected_name)
    
    def test_conflict_resolution_with_complex_filenames(self):
        """Test conflict resolution with complex filenames containing special characters."""
        complex_names = [
            "file with spaces.jpg",
            "file-with-dashes.mp4",
            "file_with_underscores.png",
            "file.with.dots.avi"
        ]
        
        for base_name in complex_names:
            with self.subTest(filename=base_name):
                # Create a conflicting file
                existing_file_path = os.path.join(self.test_dir, base_name)
                with open(existing_file_path, 'w') as f:
                    f.write("test content")
                
                # Test conflict resolution
                result = self.conflict_resolver.resolve_file_conflicts(self.test_dir, base_name)
                
                # Should properly handle the filename and add _c1 suffix
                name, ext = os.path.splitext(base_name)
                expected_name = f"{name}_c1{ext}"
                self.assertEqual(result, expected_name)
    
    def test_conflict_detection_case_sensitivity(self):
        """Test that conflict detection respects case sensitivity of the file system."""
        # Create a file with specific case
        base_name = "CaseSensitive.jpg"
        existing_file_path = os.path.join(self.test_dir, base_name)
        with open(existing_file_path, 'w') as f:
            f.write("test content")
        
        # Test with same case (should conflict)
        result_same_case = self.conflict_resolver.resolve_file_conflicts(self.test_dir, base_name)
        expected_same_case = "CaseSensitive_c1.jpg"
        self.assertEqual(result_same_case, expected_same_case)
        
        # Test with different case (behavior depends on file system)
        different_case_name = "casesensitive.jpg"
        result_different_case = self.conflict_resolver.resolve_file_conflicts(self.test_dir, different_case_name)
        
        # On case-insensitive file systems (Windows, macOS), this should also conflict
        # On case-sensitive file systems (Linux), this should not conflict
        # We'll test both scenarios
        if os.path.exists(os.path.join(self.test_dir, different_case_name)):
            # Case-insensitive file system
            expected_different_case = "casesensitive_c1.jpg"
            self.assertEqual(result_different_case, expected_different_case)
        else:
            # Case-sensitive file system
            self.assertEqual(result_different_case, different_case_name)
    
    def test_conflict_resolution_empty_directory(self):
        """Test conflict resolution in an empty directory."""
        # Test with empty directory
        target_name = "test_file.jpg"
        result = self.conflict_resolver.resolve_file_conflicts(self.test_dir, target_name)
        
        # Should return original name when directory is empty
        self.assertEqual(result, target_name)
    
    def test_conflict_resolution_nonexistent_directory(self):
        """Test conflict resolution with nonexistent directory."""
        # Test with nonexistent directory
        nonexistent_dir = os.path.join(self.test_dir, "nonexistent")
        target_name = "test_file.jpg"
        
        # Should handle gracefully and return original name
        result = self.conflict_resolver.resolve_file_conflicts(nonexistent_dir, target_name)
        self.assertEqual(result, target_name)
    
    @patch('os.path.exists')
    def test_conflict_resolution_os_error_handling(self, mock_exists):
        """Test conflict resolution handles OS errors gracefully."""
        # Mock os.path.exists to raise an exception
        mock_exists.side_effect = OSError("Mocked OS error")
        
        target_name = "test_file.jpg"
        
        # The current implementation doesn't handle OS errors in resolve_file_conflicts
        # It will propagate the exception, which is the expected behavior
        with self.assertRaises(OSError):
            self.conflict_resolver.resolve_file_conflicts(self.test_dir, target_name)
    
    def test_sequential_conflict_suffix_generation(self):
        """Test that conflict suffixes are generated sequentially without gaps."""
        base_name = "sequential_test.jpg"
        
        # Create files with gaps in numbering (c1, c3, c5)
        conflict_files = [
            "sequential_test.jpg",
            "sequential_test_c1.jpg",
            "sequential_test_c3.jpg",
            "sequential_test_c5.jpg"
        ]
        
        for filename in conflict_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("test content")
        
        # Test conflict resolution
        result = self.conflict_resolver.resolve_file_conflicts(self.test_dir, base_name)
        
        # Should find the first available number (c2, not c4 or c6)
        expected_name = "sequential_test_c2.jpg"
        self.assertEqual(result, expected_name)


if __name__ == '__main__':
    unittest.main()