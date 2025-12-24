"""
Unit tests for session logging functionality.

Tests session log creation, saving, and log directory management.
"""

import unittest
import tempfile
import shutil
import os
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from logging_manager import LoggingManager
from file_operations import FileOperations, FileInfo, ProcessResult, OperationLog


class TestSessionLogging(unittest.TestCase):
    """Test cases for session logging functionality."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.logs_dir = os.path.join(self.test_dir, "logs")
        self.logging_manager = LoggingManager(logs_dir=self.logs_dir)
        
        # Setup application logger for testing
        self.app_logger = self.logging_manager.setup_application_logger("DEBUG")
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_session_log_creation(self):
        """Test session log creation and initialization."""
        # Setup session logger
        session_logger = self.logging_manager.setup_session_logger()
        
        # Verify session logger was created
        self.assertIsNotNone(session_logger)
        self.assertIsNotNone(self.logging_manager.session_start_time)
        self.assertEqual(len(self.logging_manager.session_entries), 0)
        
        # Verify logs directory was created
        self.assertTrue(os.path.exists(self.logs_dir))
        
        # Verify session log file was created
        session_files = list(Path(self.logs_dir).glob("session_*.log"))
        self.assertEqual(len(session_files), 1)
    
    def test_session_log_operations(self):
        """Test logging of various file operations."""
        # Setup session logger
        self.logging_manager.setup_session_logger()
        
        # Test rename operation logging
        self.logging_manager.log_operation("rename", {
            "old_name": "IMG_001.jpg",
            "new_name": "2023-01-15_12-30-45_City.jpg",
            "folder_path": "/test/folder"
        })
        
        # Test skip operation logging
        self.logging_manager.log_operation("skip", {
            "filename": "IMG_002.jpg",
            "reason": "No metadata available",
            "folder_path": "/test/folder"
        })
        
        # Test error operation logging
        self.logging_manager.log_operation("error", {
            "filename": "IMG_003.jpg",
            "error_message": "Permission denied",
            "folder_path": "/test/folder"
        })
        
        # Verify operations were logged
        self.assertEqual(len(self.logging_manager.session_entries), 3)
        
        # Check rename operation
        rename_entry = self.logging_manager.session_entries[0]
        self.assertEqual(rename_entry["operation"], "rename")
        self.assertEqual(rename_entry["old_name"], "IMG_001.jpg")
        self.assertEqual(rename_entry["new_name"], "2023-01-15_12-30-45_City.jpg")
        
        # Check skip operation
        skip_entry = self.logging_manager.session_entries[1]
        self.assertEqual(skip_entry["operation"], "skip")
        self.assertEqual(skip_entry["filename"], "IMG_002.jpg")
        self.assertEqual(skip_entry["reason"], "No metadata available")
        
        # Check error operation
        error_entry = self.logging_manager.session_entries[2]
        self.assertEqual(error_entry["operation"], "error")
        self.assertEqual(error_entry["filename"], "IMG_003.jpg")
        self.assertEqual(error_entry["error_message"], "Permission denied")
    
    def test_session_log_saving(self):
        """Test session log saving to JSON file."""
        # Setup session logger and log some operations
        self.logging_manager.setup_session_logger()
        
        self.logging_manager.log_operation("rename", {
            "old_name": "test1.jpg",
            "new_name": "renamed1.jpg"
        })
        
        self.logging_manager.log_operation("skip", {
            "filename": "test2.jpg",
            "reason": "No metadata"
        })
        
        # Save session log
        saved_path = self.logging_manager.save_session_log()
        
        # Verify file was saved
        self.assertIsNotNone(saved_path)
        self.assertTrue(os.path.exists(saved_path))
        self.assertTrue(saved_path.endswith('.json'))
        
        # Verify file content
        with open(saved_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        self.assertIn("session_start", session_data)
        self.assertIn("session_end", session_data)
        self.assertIn("total_operations", session_data)
        self.assertIn("operations", session_data)
        
        self.assertEqual(session_data["total_operations"], 2)
        self.assertEqual(len(session_data["operations"]), 2)
        
        # Check operation details
        operations = session_data["operations"]
        self.assertEqual(operations[0]["operation"], "rename")
        self.assertEqual(operations[0]["old_name"], "test1.jpg")
        self.assertEqual(operations[1]["operation"], "skip")
        self.assertEqual(operations[1]["filename"], "test2.jpg")
    
    def test_session_log_empty_save(self):
        """Test saving session log when no operations were logged."""
        # Setup session logger but don't log any operations
        self.logging_manager.setup_session_logger()
        
        # Try to save empty session
        saved_path = self.logging_manager.save_session_log()
        
        # Should return None for empty session
        self.assertIsNone(saved_path)
    
    def test_session_log_without_setup(self):
        """Test saving session log without setting up session logger."""
        # Try to save without setup
        saved_path = self.logging_manager.save_session_log()
        
        # Should return None
        self.assertIsNone(saved_path)
    
    def test_log_directory_creation(self):
        """Test automatic creation of logs directory."""
        # Use a non-existent directory
        new_logs_dir = os.path.join(self.test_dir, "new_logs")
        self.assertFalse(os.path.exists(new_logs_dir))
        
        # Create logging manager with new directory
        new_logging_manager = LoggingManager(logs_dir=new_logs_dir)
        
        # Directory should be created during initialization
        self.assertTrue(os.path.exists(new_logs_dir))
    
    def test_session_summary(self):
        """Test session summary generation."""
        # Setup session logger and log operations
        self.logging_manager.setup_session_logger()
        
        self.logging_manager.log_operation("rename", {"old_name": "test1.jpg", "new_name": "new1.jpg"})
        self.logging_manager.log_operation("rename", {"old_name": "test2.jpg", "new_name": "new2.jpg"})
        self.logging_manager.log_operation("skip", {"filename": "test3.jpg", "reason": "No metadata"})
        self.logging_manager.log_operation("error", {"filename": "test4.jpg", "error_message": "Permission denied"})
        
        # Get session summary
        summary = self.logging_manager.get_session_summary()
        
        # Verify summary content
        self.assertEqual(summary["total_operations"], 4)
        self.assertIn("operation_counts", summary)
        self.assertIn("session_start", summary)
        
        # Check operation counts
        counts = summary["operation_counts"]
        self.assertEqual(counts["rename"], 2)
        self.assertEqual(counts["skip"], 1)
        self.assertEqual(counts["error"], 1)
    
    def test_session_summary_empty(self):
        """Test session summary when no operations logged."""
        # Get summary without logging operations
        summary = self.logging_manager.get_session_summary()
        
        # Should return minimal summary
        self.assertEqual(summary["total_operations"], 0)
        self.assertNotIn("operation_counts", summary)
    
    def test_session_log_error_handling(self):
        """Test error handling in session logging."""
        # Setup session logger
        self.logging_manager.setup_session_logger()
        
        # Test logging with invalid data (should not crash)
        try:
            self.logging_manager.log_operation("test", {"invalid": object()})
            # Should handle gracefully and continue
        except Exception as e:
            self.fail(f"Session logging should handle invalid data gracefully: {e}")
        
        # Test saving to invalid path
        with patch.object(self.logging_manager, 'logs_dir', Path("/invalid/path")):
            saved_path = self.logging_manager.save_session_log()
            # Should return None on save failure
            self.assertIsNone(saved_path)
    
    def test_file_operations_session_integration(self):
        """Test integration of session logging with file operations."""
        # Create test files
        test_folder = os.path.join(self.test_dir, "test_files")
        os.makedirs(test_folder)
        
        test_file1 = os.path.join(test_folder, "test1.jpg")
        test_file2 = os.path.join(test_folder, "test2.jpg")
        
        with open(test_file1, 'w') as f:
            f.write("test content")
        with open(test_file2, 'w') as f:
            f.write("test content")
        
        # Setup file operations with logging manager
        supported_extensions = {'.jpg', '.jpeg', '.png'}
        file_ops = FileOperations(supported_extensions, logger=self.app_logger, logging_manager=self.logging_manager)
        
        # Setup session logger
        self.logging_manager.setup_session_logger()
        
        # Create file infos for processing
        file_infos = [
            FileInfo(
                original_name="test1.jpg",
                original_path=test_file1,
                new_name="renamed1.jpg",
                final_name="renamed1.jpg",
                location="Test Location",
                city="Test City",
                has_metadata=True,
                selected=True
            ),
            FileInfo(
                original_name="test2.jpg",
                original_path=test_file2,
                new_name="renamed2.jpg",
                final_name="renamed2.jpg",
                location="Test Location",
                city="Test City",
                has_metadata=True,
                selected=True
            )
        ]
        
        # Process files
        result = file_ops.process_files(test_folder, file_infos)
        
        # Verify session logging occurred
        self.assertGreater(len(self.logging_manager.session_entries), 0)
        
        # Check for session start and completion logs
        operations = [entry["operation"] for entry in self.logging_manager.session_entries]
        self.assertIn("session_start", operations)
        self.assertIn("session_complete", operations)
        
        # Check for rename operations
        rename_operations = [entry for entry in self.logging_manager.session_entries if entry["operation"] == "rename"]
        self.assertEqual(len(rename_operations), 2)
    
    def test_session_log_file_naming(self):
        """Test session log file naming with timestamps."""
        # Setup multiple session loggers to test naming
        session1_logger = self.logging_manager.setup_session_logger()
        
        # Log an operation and save
        self.logging_manager.log_operation("test", {"data": "test1"})
        saved_path1 = self.logging_manager.save_session_log()
        
        # Wait a moment and create another session
        import time
        time.sleep(1)
        
        # Reset for new session
        self.logging_manager.session_entries.clear()
        self.logging_manager.session_start_time = None
        
        session2_logger = self.logging_manager.setup_session_logger()
        self.logging_manager.log_operation("test", {"data": "test2"})
        saved_path2 = self.logging_manager.save_session_log()
        
        # Verify both files were created with different names
        self.assertIsNotNone(saved_path1)
        self.assertIsNotNone(saved_path2)
        self.assertNotEqual(saved_path1, saved_path2)
        
        # Verify both files exist
        self.assertTrue(os.path.exists(saved_path1))
        self.assertTrue(os.path.exists(saved_path2))
        
        # Verify file naming pattern
        self.assertTrue(os.path.basename(saved_path1).startswith("session_"))
        self.assertTrue(os.path.basename(saved_path1).endswith(".json"))
        self.assertTrue(os.path.basename(saved_path2).startswith("session_"))
        self.assertTrue(os.path.basename(saved_path2).endswith(".json"))


if __name__ == '__main__':
    unittest.main()