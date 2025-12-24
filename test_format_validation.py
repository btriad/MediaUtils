"""
Unit tests for format validation system.

Tests the FormatValidator class and enhanced validation functionality
in the filename generator module.
"""

import unittest
from datetime import datetime
from filename_generator import FormatValidator, ValidationSeverity, ValidationResult, FilenameGenerator


class TestFormatValidator(unittest.TestCase):
    """Test cases for the FormatValidator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = FormatValidator()
    
    def test_valid_format_patterns(self):
        """Test validation of various valid format patterns."""
        valid_formats = [
            "%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}",
            "%Y-%m-%d_{city}_{increment:03d}.{ext}",
            "%B_%d_%Y_{increment:03d}.{ext}",
            "%Y%m%d_{increment:02d}.{ext}",
            "%d.%m.%Y-{increment}.{ext}",
            "%Y-%m-%d_{increment:04d}.{ext}"
        ]
        
        for format_str in valid_formats:
            with self.subTest(format_str=format_str):
                result = self.validator.validate_format_realtime(format_str)
                self.assertTrue(result.is_valid, 
                              f"Format '{format_str}' should be valid. Errors: {[msg.message for msg in result.errors]}")
                self.assertIsNotNone(result.example, "Valid format should generate example")
    
    def test_missing_required_placeholders(self):
        """Test detection of missing required placeholders."""
        invalid_formats = [
            "%Y.%m.%d-%H.%M.%S.{increment:03d}",  # Missing {ext}
            "%Y-%m-%d_{city}_{increment:03d}",     # Missing {ext}
            "just_text_no_extension"               # Missing {ext}
        ]
        
        for format_str in invalid_formats:
            with self.subTest(format_str=format_str):
                result = self.validator.validate_format_realtime(format_str)
                self.assertFalse(result.is_valid, f"Format '{format_str}' should be invalid")
                self.assertTrue(any("Missing required placeholder: {ext}" in msg.message 
                                  for msg in result.errors))
    
    def test_invalid_filename_characters(self):
        """Test detection of invalid filename characters."""
        invalid_formats = [
            "%Y.%m.%d<test>.{ext}",     # Contains <
            "%Y.%m.%d>test.{ext}",      # Contains >
            "%Y.%m.%d:test.{ext}",      # Contains :
            "%Y.%m.%d\"test\".{ext}",   # Contains "
            "%Y.%m.%d|test.{ext}",      # Contains |
            "%Y.%m.%d?test.{ext}",      # Contains ?
            "%Y.%m.%d*test.{ext}",      # Contains *
            "%Y.%m.%d\\test.{ext}",     # Contains \
            "%Y.%m.%d/test.{ext}"       # Contains /
        ]
        
        for format_str in invalid_formats:
            with self.subTest(format_str=format_str):
                result = self.validator.validate_format_realtime(format_str)
                self.assertFalse(result.is_valid, f"Format '{format_str}' should be invalid")
                self.assertTrue(any("Invalid character" in msg.message 
                                  for msg in result.errors))
    
    def test_invalid_strftime_codes(self):
        """Test detection of invalid strftime codes."""
        invalid_formats = [
            "%Z.%m.%d.{ext}",           # Invalid %Z
            "%year.%month.%day.{ext}",  # Invalid long codes
            "%X.%m.%d.{ext}",           # Invalid %X
            "%Q.%m.%d.{ext}"            # Invalid %Q
        ]
        
        for format_str in invalid_formats:
            with self.subTest(format_str=format_str):
                result = self.validator.validate_format_realtime(format_str)
                self.assertFalse(result.is_valid, f"Format '{format_str}' should be invalid")
                self.assertTrue(any("Invalid strftime code" in msg.message 
                                  for msg in result.errors))
    
    def test_invalid_custom_placeholders(self):
        """Test detection of invalid custom placeholders."""
        invalid_formats = [
            "%Y.%m.%d.{invalid}.{ext}",         # Invalid placeholder
            "%Y.%m.%d.{extension}.{ext}",       # Should be {ext}
            "%Y.%m.%d.{inc}.{ext}",             # Should be {increment:03d}
            "%Y.%m.%d.{number}.{ext}",          # Should be {increment:03d}
            "%Y.%m.%d.{location}.{ext}"         # Should be {city}
        ]
        
        for format_str in invalid_formats:
            with self.subTest(format_str=format_str):
                result = self.validator.validate_format_realtime(format_str)
                self.assertFalse(result.is_valid, f"Format '{format_str}' should be invalid")
                self.assertTrue(any("Invalid placeholder" in msg.message 
                                  for msg in result.errors))
    
    def test_unmatched_braces(self):
        """Test detection of unmatched braces."""
        invalid_formats = [
            "%Y.%m.%d.{increment:03d.{ext}",    # Missing closing brace
            "%Y.%m.%d.increment:03d}.{ext}",    # Missing opening brace
            "%Y.%m.%d.{increment:03d}.ext}",    # Extra closing brace
            "%Y.%m.%d.{{increment:03d}.{ext}"   # Extra opening brace
        ]
        
        for format_str in invalid_formats:
            with self.subTest(format_str=format_str):
                result = self.validator.validate_format_realtime(format_str)
                self.assertFalse(result.is_valid, f"Format '{format_str}' should be invalid")
                self.assertTrue(any("Unmatched" in msg.message and "brace" in msg.message 
                                  for msg in result.errors))
    
    def test_empty_format(self):
        """Test validation of empty format string."""
        result = self.validator.validate_format_realtime("")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Format cannot be empty" in msg.message 
                          for msg in result.errors))
        
        result = self.validator.validate_format_realtime("   ")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("Format cannot be empty" in msg.message 
                          for msg in result.errors))
    
    def test_error_message_generation(self):
        """Test that appropriate error messages are generated."""
        # Test missing extension
        result = self.validator.validate_format_realtime("%Y.%m.%d")
        error_messages = [msg.message for msg in result.errors]
        self.assertIn("Missing required placeholder: {ext}", error_messages)
        
        # Test invalid character
        result = self.validator.validate_format_realtime("%Y.%m.%d<test>.{ext}")
        error_messages = [msg.message for msg in result.errors]
        self.assertTrue(any("Invalid character '<'" in msg for msg in error_messages))
        
        # Test invalid strftime code
        result = self.validator.validate_format_realtime("%Z.%m.%d.{ext}")
        error_messages = [msg.message for msg in result.errors]
        self.assertTrue(any("Invalid strftime code '%Z'" in msg for msg in error_messages))
    
    def test_format_suggestions(self):
        """Test generation of format suggestions."""
        suggestions = self.validator.get_format_suggestions()
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # All suggestions should be valid
        for suggestion in suggestions:
            with self.subTest(suggestion=suggestion):
                result = self.validator.validate_format_realtime(suggestion)
                self.assertTrue(result.is_valid, 
                              f"Suggested format '{suggestion}' should be valid")
    
    def test_correction_suggestions(self):
        """Test generation of correction suggestions."""
        # Test common mistakes
        test_cases = [
            ("{inc}", "increment"),
            ("{extension}", "ext"),
            ("{location}", "city"),
            ("%year", "year")
        ]
        
        for invalid_part, expected_word in test_cases:
            format_str = f"%Y.%m.%d.{invalid_part}.{{ext}}" if not invalid_part.startswith('%') else f"{invalid_part}.%m.%d.{{ext}}"
            result = self.validator.validate_format_realtime(format_str)
            
            # Should have suggestions
            suggestions = [msg.suggestion for msg in result.messages if msg.suggestion]
            self.assertGreater(len(suggestions), 0, 
                             f"Should have suggestions for '{invalid_part}'")
            
            # At least one suggestion should mention the expected word
            has_relevant_suggestion = any(expected_word in suggestion.lower() 
                                        for suggestion in suggestions)
            self.assertTrue(has_relevant_suggestion, 
                          f"Should suggest something related to '{expected_word}' for '{invalid_part}'")
    
    def test_example_generation(self):
        """Test generation of example filenames."""
        valid_format = "%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}"
        result = self.validator.validate_format_realtime(valid_format)
        
        self.assertTrue(result.is_valid)
        self.assertIsNotNone(result.example)
        self.assertIn("2024", result.example)  # Should contain year
        self.assertIn("001", result.example)   # Should contain increment
        self.assertIn("jpg", result.example)   # Should contain extension
    
    def test_validation_severity_levels(self):
        """Test that different severity levels are used appropriately."""
        # Error case
        result = self.validator.validate_format_realtime("%Y.%m.%d")  # Missing {ext}
        self.assertTrue(any(msg.severity == ValidationSeverity.ERROR 
                          for msg in result.messages))
        
        # Valid format with info suggestions
        result = self.validator.validate_format_realtime("%Y.%m.%d.{ext}")
        if result.messages:  # May have info suggestions
            self.assertTrue(any(msg.severity == ValidationSeverity.INFO 
                              for msg in result.messages))
    
    def test_position_information(self):
        """Test that error positions are correctly identified."""
        format_str = "%Y.%m.%d<invalid>.{ext}"
        result = self.validator.validate_format_realtime(format_str)
        
        # Should have position information for the invalid character
        positioned_errors = [msg for msg in result.errors if msg.position is not None]
        self.assertGreater(len(positioned_errors), 0, 
                         "Should provide position information for errors")
        
        # Position should be reasonable
        for error in positioned_errors:
            self.assertGreaterEqual(error.position, 0)
            self.assertLess(error.position, len(format_str))


class TestFilenameGeneratorValidation(unittest.TestCase):
    """Test cases for validation integration in FilenameGenerator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = FilenameGenerator()
    
    def test_legacy_validate_format_method(self):
        """Test backward compatibility of validate_format method."""
        # Valid format
        is_valid, error_msg = self.generator.validate_format("%Y.%m.%d.{ext}")
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
        
        # Invalid format
        is_valid, error_msg = self.generator.validate_format("%Y.%m.%d")  # Missing {ext}
        self.assertFalse(is_valid)
        self.assertNotEqual(error_msg, "")
    
    def test_detailed_validation_method(self):
        """Test the new detailed validation method."""
        result = self.generator.validate_format_detailed("%Y.%m.%d.{ext}")
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        
        result = self.generator.validate_format_detailed("%Y.%m.%d")  # Missing {ext}
        self.assertIsInstance(result, ValidationResult)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_get_available_placeholders_enhanced(self):
        """Test that available placeholders include both strftime and custom."""
        placeholders = self.generator.get_available_placeholders()
        
        # Should include strftime codes
        self.assertIn('%Y', placeholders)
        self.assertIn('%m', placeholders)
        self.assertIn('%d', placeholders)
        
        # Should include custom placeholders
        self.assertIn('{ext}', placeholders)
        self.assertIn('{increment:03d}', placeholders)
        self.assertIn('{city}', placeholders)
    
    def test_format_suggestions_method(self):
        """Test the format suggestions method."""
        suggestions = self.generator.get_format_suggestions()
        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)
        
        # All suggestions should be valid
        for suggestion in suggestions:
            is_valid, _ = self.generator.validate_format(suggestion)
            self.assertTrue(is_valid, f"Suggested format '{suggestion}' should be valid")
    
    def test_suggest_format_corrections_method(self):
        """Test the format correction suggestions method."""
        corrections = self.generator.suggest_format_corrections("%Y.%m.%d.{inc}.{ext}")
        self.assertIsInstance(corrections, list)
        
        # Should have at least one correction for the invalid {inc} placeholder
        self.assertGreater(len(corrections), 0)


if __name__ == '__main__':
    unittest.main()