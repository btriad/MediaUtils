"""
Integration Tests for GUI Validation Feedback

Tests the real-time format validation display, error highlighting,
and validation message functionality in the GUI components.
"""

import unittest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from pathlib import Path

# Import the GUI components and related classes
from gui_components import MediaRenamerGUI
from filename_generator import ValidationResult, ValidationMessage, ValidationSeverity


class TestGUIValidation(unittest.TestCase):
    """Test GUI validation feedback functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test settings
        self.temp_dir = tempfile.mkdtemp()
        self.test_settings_file = os.path.join(self.temp_dir, "test_settings.json")
        
        # Mock the settings manager to use test directory
        with patch('gui_components.SettingsManager') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings_instance.get.side_effect = lambda key, default=None: {
                "window_geometry": "1200x600",
                "folder_path": self.temp_dir,
                "filename_format": "%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}"
            }.get(key, default)
            mock_settings_instance.validate_folder_path.return_value = True
            mock_settings.return_value = mock_settings_instance
            
            # Create GUI instance
            self.gui = MediaRenamerGUI()
            self.root = self.gui.root
    
    def tearDown(self):
        """Clean up test environment."""
        try:
            self.root.destroy()
        except:
            pass
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_validation_status_indicator_valid_format(self):
        """Test validation status indicator shows correct status for valid format."""
        # Create a mock validation result with no messages (perfect format)
        mock_validation = ValidationResult(
            is_valid=True,
            messages=[],
            example="2024.06.30-14.32.55.001.jpg"
        )
        
        # Mock the validation method to return our test result
        with patch.object(self.gui.filename_generator, 'validate_format_detailed', return_value=mock_validation):
            self.gui.format_var.set("%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}")
            self.gui.update_format_validation()
        
        # Check validation status
        status_text = self.gui.validation_status_label.cget("text")
        status_color = self.gui.validation_status_label.cget("foreground")
        
        self.assertIn("✓", status_text)
        self.assertIn("Valid", status_text)
        self.assertEqual(str(status_color), "green")
    
    def test_validation_status_indicator_invalid_format(self):
        """Test validation status indicator shows error for invalid format."""
        # Set an invalid format (missing required {ext})
        invalid_format = "%Y.%m.%d-%H.%M.%S.{increment:03d}"
        self.gui.format_var.set(invalid_format)
        
        # Trigger validation update
        self.gui.update_format_validation()
        
        # Check validation status
        status_text = self.gui.validation_status_label.cget("text")
        status_color = self.gui.validation_status_label.cget("foreground")
        
        self.assertIn("✗", status_text)
        self.assertIn("Invalid", status_text)
        self.assertEqual(str(status_color), "red")
    
    def test_validation_messages_display_errors(self):
        """Test that validation error messages are displayed correctly."""
        # Set an invalid format with multiple errors
        invalid_format = "%Y.%m.%d-{increment:3d}"  # Missing {ext} and invalid increment format
        self.gui.format_var.set(invalid_format)
        
        # Trigger validation update
        self.gui.update_format_validation()
        
        # Check that validation messages are visible (check if widget is managed by grid)
        try:
            grid_info = self.gui.validation_text.grid_info()
            validation_text_visible = bool(grid_info)  # If grid_info is not empty, widget is visible
        except tk.TclError:
            validation_text_visible = False
        self.assertTrue(validation_text_visible, "Validation messages should be visible for invalid format")
        
        # Check validation text content
        validation_content = self.gui.validation_text.get(1.0, tk.END)
        self.assertIn("Errors:", validation_content)
        self.assertIn("{ext}", validation_content)  # Should mention missing {ext}
    
    def test_validation_messages_display_warnings(self):
        """Test that validation warning messages are displayed correctly."""
        # Create a mock validation result with warnings
        mock_validation = ValidationResult(
            is_valid=True,
            messages=[
                ValidationMessage(
                    ValidationSeverity.WARNING,
                    "Format may generate reserved filename 'CON'",
                    "Consider adding a prefix to avoid Windows reserved names"
                )
            ],
            example="Example: 2024.06.30-14.32.55.001.jpg"
        )
        
        # Mock the validation method to return our test result
        with patch.object(self.gui.filename_generator, 'validate_format_detailed', return_value=mock_validation):
            self.gui.format_var.set("CON.{increment:03d}.{ext}")
            self.gui.update_format_validation()
        
        # Check that validation messages are visible (check if widget is managed by grid)
        try:
            grid_info = self.gui.validation_text.grid_info()
            validation_text_visible = bool(grid_info)  # If grid_info is not empty, widget is visible
        except tk.TclError:
            validation_text_visible = False
        self.assertTrue(validation_text_visible, "Validation messages should be visible for warnings")
        
        # Check validation text content
        validation_content = self.gui.validation_text.get(1.0, tk.END)
        self.assertIn("Warnings:", validation_content)
        self.assertIn("reserved filename", validation_content)
    
    def test_validation_messages_display_suggestions(self):
        """Test that validation suggestions are displayed correctly."""
        # Create a mock validation result with info suggestions
        mock_validation = ValidationResult(
            is_valid=True,
            messages=[
                ValidationMessage(
                    ValidationSeverity.INFO,
                    "Consider adding {city} to include location information",
                    "Add {city} to use GPS location data in filenames"
                )
            ],
            example="Example: 2024.06.30-14.32.55.001.jpg"
        )
        
        # Mock the validation method to return our test result
        with patch.object(self.gui.filename_generator, 'validate_format_detailed', return_value=mock_validation):
            self.gui.format_var.set("%Y.%m.%d.{increment:03d}.{ext}")
            self.gui.update_format_validation()
        
        # Check that validation messages are visible (check if widget is managed by grid)
        try:
            grid_info = self.gui.validation_text.grid_info()
            validation_text_visible = bool(grid_info)  # If grid_info is not empty, widget is visible
        except tk.TclError:
            validation_text_visible = False
        self.assertTrue(validation_text_visible, "Validation messages should be visible for suggestions")
        
        # Check validation text content
        validation_content = self.gui.validation_text.get(1.0, tk.END)
        self.assertIn("Suggestions:", validation_content)
        self.assertIn("{city}", validation_content)
    
    def test_validation_messages_hidden_for_valid_format(self):
        """Test that validation messages are hidden for completely valid format."""
        # Create a mock validation result with no messages
        mock_validation = ValidationResult(
            is_valid=True,
            messages=[],
            example="Example: 2024.06.30-14.32.55.001.jpg"
        )
        
        # Mock the validation method to return our test result
        with patch.object(self.gui.filename_generator, 'validate_format_detailed', return_value=mock_validation):
            self.gui.format_var.set("%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}")
            self.gui.update_format_validation()
        
        # Check that validation messages are hidden (check if widget is managed by grid)
        try:
            grid_info = self.gui.validation_text.grid_info()
            validation_text_visible = bool(grid_info)  # If grid_info is not empty, widget is visible
        except tk.TclError:
            validation_text_visible = False
        self.assertFalse(validation_text_visible, "Validation messages should be hidden for valid format with no suggestions")
    
    def test_real_time_validation_debouncing(self):
        """Test that validation updates are debounced to avoid excessive calls."""
        # Mock the validation method to track calls
        with patch.object(self.gui.filename_generator, 'validate_format_detailed') as mock_validate:
            mock_validate.return_value = ValidationResult(True, [], "Example: test.jpg")
            
            # Rapidly change the format multiple times
            self.gui.format_var.set("%Y")
            self.gui.format_var.set("%Y.%m")
            self.gui.format_var.set("%Y.%m.%d")
            self.gui.format_var.set("%Y.%m.%d.{ext}")
            
            # Process any pending after() calls
            self.root.update()
            
            # Should have been called only once due to debouncing
            # (or at least fewer times than the number of changes)
            self.assertLessEqual(mock_validate.call_count, 2, 
                               "Validation should be debounced to reduce excessive calls")
    
    def test_example_update_with_validation(self):
        """Test that example is updated correctly with validation."""
        # Create a mock validation result with a proper example
        mock_validation = ValidationResult(
            is_valid=True,
            messages=[],
            example="2024.06.30-NeoPsihiko.001.jpg"
        )
        
        # Mock the validation method to return our test result
        with patch.object(self.gui.filename_generator, 'validate_format_detailed', return_value=mock_validation):
            self.gui.format_var.set("%Y.%m.%d-{city}.{increment:03d}.{ext}")
            self.gui.update_format_validation()
        
        # Check example label
        example_text = self.gui.example_label.cget("text")
        example_color = self.gui.example_label.cget("foreground")
        
        self.assertIn("Example:", example_text)
        self.assertIn("2024", example_text)  # Should contain year
        self.assertIn("NeoPsihiko", example_text)  # Should contain sample city
        self.assertIn("001", example_text)  # Should contain increment
        self.assertIn("jpg", example_text)  # Should contain extension
        self.assertEqual(str(example_color), "gray")  # Should be gray for valid
    
    def test_example_error_display(self):
        """Test that example shows error for invalid format."""
        # Set an invalid format
        invalid_format = "%Y.%m.%d-{invalid_placeholder}.{ext}"
        self.gui.format_var.set(invalid_format)
        
        # Trigger validation update
        self.gui.update_format_validation()
        
        # Check example label shows error
        example_text = self.gui.example_label.cget("text")
        example_color = self.gui.example_label.cget("foreground")
        
        self.assertIn("Invalid", example_text)
        self.assertEqual(str(example_color), "red")
    
    def test_format_suggestions_dialog(self):
        """Test that format suggestions dialog can be opened."""
        # Mock the suggestions method
        mock_suggestions = [
            "%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}",
            "%Y-%m-%d_{city}_{increment:03d}.{ext}",
            "%Y%m%d_%H%M%S_{increment:03d}.{ext}"
        ]
        
        with patch.object(self.gui.filename_generator, 'get_format_suggestions', return_value=mock_suggestions):
            # This should not raise an exception
            try:
                self.gui.show_format_suggestions()
                # Close the dialog immediately
                for widget in self.root.winfo_children():
                    if isinstance(widget, tk.Toplevel):
                        widget.destroy()
                        break
            except Exception as e:
                self.fail(f"Format suggestions dialog failed to open: {e}")
    
    def test_validation_prevents_processing_invalid_format(self):
        """Test that file processing is prevented when format is invalid."""
        # Set up some mock file infos
        self.gui.file_infos = [Mock(selected=True)]
        
        # Set invalid format and update validation
        invalid_format = "%Y.%m.%d"  # Missing {ext}
        self.gui.format_var.set(invalid_format)
        self.gui.update_format_validation()
        
        # Mock messagebox to capture the error
        with patch('gui_components.messagebox') as mock_messagebox:
            # Try to process files
            self.gui.process_files()
            
            # Should show error message about invalid format
            mock_messagebox.showerror.assert_called_once()
            call_args = mock_messagebox.showerror.call_args[0]
            self.assertIn("Invalid Format", call_args[0])
            self.assertIn("fix", call_args[1].lower())


class TestGUIProgressIndicators(unittest.TestCase):
    """Test GUI progress indicator functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for test settings
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock the settings manager
        with patch('gui_components.SettingsManager') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings_instance.get.side_effect = lambda key, default=None: {
                "window_geometry": "1200x600",
                "folder_path": self.temp_dir,
                "filename_format": "%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}"
            }.get(key, default)
            mock_settings.return_value = mock_settings_instance
            
            # Create GUI instance
            self.gui = MediaRenamerGUI()
            self.root = self.gui.root
    
    def tearDown(self):
        """Clean up test environment."""
        try:
            self.root.destroy()
        except:
            pass
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_progress_bar_show_hide(self):
        """Test progress bar show and hide functionality."""
        # Initially progress bar should be hidden
        try:
            grid_info = self.gui.progress_bar.grid_info()
            progress_bar_visible = bool(grid_info)
        except tk.TclError:
            progress_bar_visible = False
        self.assertFalse(progress_bar_visible, "Progress bar should be initially hidden")
        
        # Show progress bar
        self.gui.show_progress_bar()
        # Force update to ensure widget is displayed
        self.root.update_idletasks()
        # Check if widget is managed by grid
        try:
            grid_info = self.gui.progress_bar.grid_info()
            progress_bar_visible = bool(grid_info)
        except tk.TclError:
            progress_bar_visible = False
        self.assertTrue(progress_bar_visible, "Progress bar should be visible after show_progress_bar()")
        self.assertEqual(self.gui.progress_bar['value'], 0)
        
        # Hide progress bar
        self.gui.hide_progress_bar()
        # Force update to ensure widget is hidden
        self.root.update_idletasks()
        # Check if widget is managed by grid
        try:
            grid_info = self.gui.progress_bar.grid_info()
            progress_bar_visible = bool(grid_info)
        except tk.TclError:
            progress_bar_visible = False
        self.assertFalse(progress_bar_visible, "Progress bar should be hidden after hide_progress_bar()")
    
    def test_progress_update(self):
        """Test progress bar update functionality."""
        # Show progress bar
        self.gui.show_progress_bar()
        
        # Update progress
        self.gui.update_progress(50, "Processing files...")
        
        # Check progress value and status message
        self.assertEqual(self.gui.progress_bar['value'], 50)
        self.assertEqual(self.gui.status_label.cget("text"), "Processing files...")
        
        # Update to completion
        self.gui.update_progress(100, "Complete")
        self.assertEqual(self.gui.progress_bar['value'], 100)
        self.assertEqual(self.gui.status_label.cget("text"), "Complete")
    
    def test_logging_status_update(self):
        """Test logging status indicator update."""
        # Update logging status
        self.gui.update_logging_status("Initializing...")
        
        # Check status label
        status_text = self.gui.logging_status_label.cget("text")
        self.assertIn("Logging:", status_text)
        self.assertIn("Initializing...", status_text)
        
        # Update to different status
        self.gui.update_logging_status("Session active")
        status_text = self.gui.logging_status_label.cget("text")
        self.assertIn("Session active", status_text)
    
    def test_progress_during_file_discovery(self):
        """Test progress indicators during file discovery operation."""
        # Create some test files
        test_files = []
        for i in range(3):
            test_file = os.path.join(self.temp_dir, f"test{i}.jpg")
            Path(test_file).touch()
            test_files.append(test_file)
        
        # Mock file operations to return our test files
        with patch.object(self.gui.file_operations, 'discover_files') as mock_discover:
            mock_discover.return_value = test_files
            
            # Mock media processor methods
            with patch.object(self.gui.media_processor, 'get_file_date') as mock_date:
                with patch.object(self.gui.media_processor, 'get_location_and_city') as mock_location:
                    mock_date.return_value = (None, False)
                    mock_location.return_value = ("", "")
                    
                    # Set folder path and trigger file discovery
                    self.gui.folder_var.set(self.temp_dir)
                    
                    # This should show progress indicators
                    self.gui.show_files()
                    
                    # Progress bar should have been shown and hidden
                    # (Note: This is a basic test - in real usage, timing might make this tricky to test)
                    
                    # Check that files were processed
                    self.assertEqual(len(self.gui.file_infos), 3)


if __name__ == '__main__':
    # Run tests with minimal GUI interaction
    unittest.main(verbosity=2)