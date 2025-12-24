"""
Integration tests for enhanced file operations with duplicate and conflict handling.

Tests the complete file processing workflow including:
- End-to-end file processing with duplicates and conflicts
- Operation logging and result reporting
- Integration of duplicate resolver and conflict resolver

Requirements tested:
- 1.1: Multiple files generating same filename get sequential numbers
- 3.1: Target filename conflicts get "_c1" suffix
- 8.2: Operation logs record old name, new name, and timestamp
"""

import unittest
import tempfile
import os
import shutil
from datetime import datetime
from unittest.mock import MagicMock, patch

from file_operations import FileOperations, FileInfo, ProcessResult, OperationLog


class TestEnhancedFileOperations(unittest.TestCase):
    """Integration tests for enhanced file operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.file_ops = FileOperations({'.jpg', '.mp4', '.png'})
        self.test_dir = tempfile.mkdtemp()
        
        # Create some test files
        self.test_files = [
            "IMG_001.jpg",
            "IMG_002.jpg", 
            "IMG_003.jpg",
            "VIDEO_001.mp4"
        ]
        
        for filename in self.test_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write(f"test content for {filename}")
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_end_to_end_processing_with_duplicates(self):
        """Test complete file processing workflow with duplicate resolution.
        
        Requirements: 1.1 - Sequential numbering for duplicate filenames
        """
        # Create FileInfo objects that will generate duplicate names
        file_infos = [
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(self.test_dir, "IMG_001.jpg"),
                new_name="2024.06.15-14.30.45.001.jpg",
                final_name="2024.06.15-14.30.45.001.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="IMG_002.jpg",
                original_path=os.path.join(self.test_dir, "IMG_002.jpg"),
                new_name="2024.06.15-14.30.45.001.jpg",  # Same as first - will create duplicate
                final_name="2024.06.15-14.30.45.001.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="IMG_003.jpg",
                original_path=os.path.join(self.test_dir, "IMG_003.jpg"),
                new_name="2024.06.15-14.30.45.001.jpg",  # Same as first - will create duplicate
                final_name="2024.06.15-14.30.45.001.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            )
        ]
        
        # Resolve duplicates and conflicts
        resolved_file_infos = self.file_ops.resolve_duplicates_and_conflicts(self.test_dir, file_infos)
        
        # Verify duplicate resolution
        final_names = [info.final_name for info in resolved_file_infos]
        expected_names = [
            "2024.06.15-14.30.45.001.jpg",
            "2024.06.15-14.30.45.001_001.jpg",
            "2024.06.15-14.30.45.001_002.jpg"
        ]
        self.assertEqual(final_names, expected_names)
        
        # Process the files
        result = self.file_ops.process_files(self.test_dir, resolved_file_infos)
        
        # Verify processing results
        self.assertEqual(result.processed_count, 3)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(len(result.operation_logs), 3)
        
        # Verify operation logs
        for i, log in enumerate(result.operation_logs):
            self.assertEqual(log.status, 'success')
            self.assertEqual(log.original_name, f"IMG_{i+1:03d}.jpg")
            self.assertEqual(log.final_name, expected_names[i])
            self.assertIsNotNone(log.timestamp)
            self.assertIsNone(log.error_message)
        
        # Verify files were actually renamed
        for expected_name in expected_names:
            expected_path = os.path.join(self.test_dir, expected_name)
            self.assertTrue(os.path.exists(expected_path), f"File {expected_name} should exist")
    
    def test_end_to_end_processing_with_conflicts(self):
        """Test complete file processing workflow with conflict resolution.
        
        Requirements: 3.1 - Conflict resolution with "_c1" suffix
        """
        # Create an existing file that will conflict
        existing_file = "existing_photo.jpg"
        existing_path = os.path.join(self.test_dir, existing_file)
        with open(existing_path, 'w') as f:
            f.write("existing content")
        
        # Create FileInfo that will conflict with existing file
        file_infos = [
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(self.test_dir, "IMG_001.jpg"),
                new_name="existing_photo.jpg",  # Will conflict with existing file
                final_name="existing_photo.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            )
        ]
        
        # Resolve duplicates and conflicts
        resolved_file_infos = self.file_ops.resolve_duplicates_and_conflicts(self.test_dir, file_infos)
        
        # Verify conflict resolution
        self.assertEqual(resolved_file_infos[0].final_name, "existing_photo_c1.jpg")
        
        # Process the files
        result = self.file_ops.process_files(self.test_dir, resolved_file_infos)
        
        # Verify processing results
        self.assertEqual(result.processed_count, 1)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(len(result.operation_logs), 1)
        
        # Verify operation log
        log = result.operation_logs[0]
        self.assertEqual(log.status, 'success')
        self.assertEqual(log.original_name, "IMG_001.jpg")
        self.assertEqual(log.final_name, "existing_photo_c1.jpg")
        self.assertIsNotNone(log.timestamp)
        self.assertIsNone(log.error_message)
        
        # Verify both files exist
        self.assertTrue(os.path.exists(existing_path))  # Original file
        conflict_path = os.path.join(self.test_dir, "existing_photo_c1.jpg")
        self.assertTrue(os.path.exists(conflict_path))  # Renamed file with conflict suffix
    
    def test_processing_with_mixed_scenarios(self):
        """Test processing with duplicates, conflicts, and various file states."""
        # Create existing files for conflicts
        existing_files = ["conflict_file.jpg", "conflict_file_c1.jpg"]
        for filename in existing_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("existing content")
        
        # Create FileInfo objects with mixed scenarios
        file_infos = [
            # Normal file
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(self.test_dir, "IMG_001.jpg"),
                new_name="normal_file.jpg",
                final_name="normal_file.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            ),
            # File with conflict
            FileInfo(
                original_name="IMG_002.jpg",
                original_path=os.path.join(self.test_dir, "IMG_002.jpg"),
                new_name="conflict_file.jpg",  # Will conflict
                final_name="conflict_file.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            ),
            # Duplicate of first file
            FileInfo(
                original_name="IMG_003.jpg",
                original_path=os.path.join(self.test_dir, "IMG_003.jpg"),
                new_name="normal_file.jpg",  # Duplicate of first
                final_name="normal_file.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            ),
            # File with no metadata (not selected)
            FileInfo(
                original_name="VIDEO_001.mp4",
                original_path=os.path.join(self.test_dir, "VIDEO_001.mp4"),
                new_name="No metadata",
                final_name="No metadata",
                location="",
                city="",
                has_metadata=False,
                selected=False  # Not selected for processing
            )
        ]
        
        # Resolve duplicates and conflicts
        resolved_file_infos = self.file_ops.resolve_duplicates_and_conflicts(self.test_dir, file_infos)
        
        # Verify resolution results
        expected_final_names = [
            "normal_file.jpg",
            "conflict_file_c2.jpg",  # c1 already exists, so c2
            "normal_file_001.jpg",   # Duplicate of first
            "No metadata"            # Unchanged
        ]
        
        actual_final_names = [info.final_name for info in resolved_file_infos]
        self.assertEqual(actual_final_names, expected_final_names)
        
        # Process the files (only selected ones)
        result = self.file_ops.process_files(self.test_dir, resolved_file_infos)
        
        # Verify processing results (only 3 selected files)
        self.assertEqual(result.processed_count, 3)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(len(result.operation_logs), 3)
        
        # Verify operation logs
        expected_log_data = [
            ("IMG_001.jpg", "normal_file.jpg", "success"),
            ("IMG_002.jpg", "conflict_file_c2.jpg", "success"),
            ("IMG_003.jpg", "normal_file_001.jpg", "success")
        ]
        
        for i, (original, final, status) in enumerate(expected_log_data):
            log = result.operation_logs[i]
            self.assertEqual(log.original_name, original)
            self.assertEqual(log.final_name, final)
            self.assertEqual(log.status, status)
            self.assertIsNotNone(log.timestamp)
            self.assertIsNone(log.error_message)
    
    def test_operation_logging_with_errors(self):
        """Test operation logging when errors occur during processing.
        
        Requirements: 8.2 - Record errors in operation logs
        """
        # Create a FileInfo for a non-existent source file
        file_infos = [
            FileInfo(
                original_name="nonexistent.jpg",
                original_path=os.path.join(self.test_dir, "nonexistent.jpg"),
                new_name="target.jpg",
                final_name="target.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            )
        ]
        
        # Process the files
        result = self.file_ops.process_files(self.test_dir, file_infos)
        
        # Verify error handling
        self.assertEqual(result.processed_count, 0)
        self.assertEqual(result.error_count, 1)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(len(result.operation_logs), 1)
        
        # Verify error log
        log = result.operation_logs[0]
        self.assertEqual(log.original_name, "nonexistent.jpg")
        self.assertEqual(log.final_name, "nonexistent.jpg")  # No change for failed files
        self.assertEqual(log.status, 'error')
        self.assertIsNotNone(log.error_message)
        self.assertIn("Source file not found", log.error_message)
        self.assertIsNotNone(log.timestamp)
    
    def test_operation_logging_with_skipped_files(self):
        """Test operation logging for files that are skipped."""
        # Create FileInfo objects with files that will be skipped
        # Note: "No metadata" files get underscore prefix (processed), only "Error:" files are truly skipped
        file_infos = [
            FileInfo(
                original_name="_IMG_001.jpg",  # Already has underscore - will be skipped
                original_path=os.path.join(self.test_dir, "_IMG_001.jpg"),
                new_name="No metadata",
                final_name="No metadata",
                location="",
                city="",
                has_metadata=False,
                selected=True
            ),
            FileInfo(
                original_name="IMG_002.jpg",
                original_path=os.path.join(self.test_dir, "IMG_002.jpg"),
                new_name="Error: some error",  # Will be skipped
                final_name="Error: some error",
                location="",
                city="",
                has_metadata=False,
                selected=True
            )
        ]
        
        # Create the file with underscore prefix
        underscore_file = os.path.join(self.test_dir, "_IMG_001.jpg")
        with open(underscore_file, 'w') as f:
            f.write("test content")
        
        # Process the files
        result = self.file_ops.process_files(self.test_dir, file_infos)
        
        # Verify skipping behavior
        self.assertEqual(result.processed_count, 0)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.skipped_count, 2)
        self.assertEqual(len(result.operation_logs), 2)
        
        # Verify skip logs
        expected_files = ["_IMG_001.jpg", "IMG_002.jpg"]
        for i, log in enumerate(result.operation_logs):
            self.assertEqual(log.original_name, expected_files[i])
            self.assertEqual(log.final_name, expected_files[i])  # No change for skipped files
            self.assertEqual(log.status, 'skipped')
            self.assertIsNotNone(log.error_message)
            self.assertIsNotNone(log.timestamp)
    
    def test_operation_logging_with_no_metadata_processing(self):
        """Test operation logging for files with no metadata that get underscore prefix."""
        # Create FileInfo object with "No metadata" that will be processed
        file_infos = [
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(self.test_dir, "IMG_001.jpg"),
                new_name="No metadata",  # Will be processed with underscore prefix
                final_name="No metadata",
                location="",
                city="",
                has_metadata=False,
                selected=True
            )
        ]
        
        # Process the files
        result = self.file_ops.process_files(self.test_dir, file_infos)
        
        # Verify processing behavior (underscore prefix is added)
        self.assertEqual(result.processed_count, 1)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.skipped_count, 0)
        self.assertEqual(len(result.operation_logs), 1)
        
        # Verify operation log
        log = result.operation_logs[0]
        self.assertEqual(log.original_name, "IMG_001.jpg")
        self.assertEqual(log.final_name, "_IMG_001.jpg")  # Underscore prefix added
        self.assertEqual(log.status, 'success')
        self.assertIsNone(log.error_message)
        self.assertIsNotNone(log.timestamp)
        
        # Verify file was actually renamed with underscore prefix
        expected_path = os.path.join(self.test_dir, "_IMG_001.jpg")
        self.assertTrue(os.path.exists(expected_path))
    
    def test_resolve_duplicates_and_conflicts_integration(self):
        """Test the integration of duplicate and conflict resolution."""
        # Create existing files for conflicts
        existing_files = ["photo.jpg", "photo_c1.jpg", "photo_001.jpg"]  # Add photo_001.jpg to force conflict
        for filename in existing_files:
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, 'w') as f:
                f.write("existing content")
        
        # Create FileInfo objects with both duplicates and conflicts
        file_infos = [
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(self.test_dir, "IMG_001.jpg"),
                new_name="photo.jpg",  # Will conflict with existing
                final_name="photo.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="IMG_002.jpg",
                original_path=os.path.join(self.test_dir, "IMG_002.jpg"),
                new_name="photo.jpg",  # Duplicate of first AND will conflict
                final_name="photo.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            )
        ]
        
        # Resolve duplicates and conflicts
        resolved_file_infos = self.file_ops.resolve_duplicates_and_conflicts(self.test_dir, file_infos)
        
        # Verify resolution: first gets conflict resolution, second gets duplicate suffix then conflict resolution
        expected_names = [
            "photo_c2.jpg",      # First file: conflicts with existing photo.jpg (photo_c1.jpg exists, so c2)
            "photo_001_c1.jpg"   # Second file: gets duplicate suffix _001, then conflicts with existing photo_001.jpg
        ]
        
        actual_names = [info.final_name for info in resolved_file_infos]
        self.assertEqual(actual_names, expected_names)
    
    def test_progress_callback_integration(self):
        """Test that progress callbacks work correctly during processing."""
        progress_calls = []
        
        def progress_callback(current, total, filename):
            progress_calls.append((current, total, filename))
        
        # Create simple FileInfo objects
        file_infos = [
            FileInfo(
                original_name="IMG_001.jpg",
                original_path=os.path.join(self.test_dir, "IMG_001.jpg"),
                new_name="photo1.jpg",
                final_name="photo1.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="IMG_002.jpg",
                original_path=os.path.join(self.test_dir, "IMG_002.jpg"),
                new_name="photo2.jpg",
                final_name="photo2.jpg",
                location="40.7128,-74.0060",
                city="TestCity",
                has_metadata=True,
                selected=True
            )
        ]
        
        # Process with progress callback
        result = self.file_ops.process_files(self.test_dir, file_infos, progress_callback)
        
        # Verify progress callbacks were called
        self.assertEqual(len(progress_calls), 2)
        self.assertEqual(progress_calls[0], (1, 2, "IMG_001.jpg"))
        self.assertEqual(progress_calls[1], (2, 2, "IMG_002.jpg"))
        
        # Verify processing succeeded
        self.assertEqual(result.processed_count, 2)
        self.assertEqual(result.error_count, 0)


if __name__ == '__main__':
    unittest.main()