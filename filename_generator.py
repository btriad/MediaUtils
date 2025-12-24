"""
Filename Generation Module

Handles the generation of new filenames based on:
- Custom format patterns
- File metadata (date, location, etc.)
- Incremental numbering for duplicates
- Real-time format validation with suggestions
"""

import os
import re
from datetime import datetime
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation messages."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationMessage:
    """Represents a validation message with severity and suggestion."""
    severity: ValidationSeverity
    message: str
    suggestion: Optional[str] = None
    position: Optional[int] = None  # Character position in format string


@dataclass
class ValidationResult:
    """Result of format validation with detailed feedback."""
    is_valid: bool
    messages: List[ValidationMessage]
    example: Optional[str] = None
    
    @property
    def errors(self) -> List[ValidationMessage]:
        """Get only error messages."""
        return [msg for msg in self.messages if msg.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationMessage]:
        """Get only warning messages."""
        return [msg for msg in self.messages if msg.severity == ValidationSeverity.WARNING]
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any error messages."""
        return len(self.errors) > 0


class FormatValidator:
    """Handles comprehensive format validation with suggestions."""
    
    def __init__(self):
        """Initialize the format validator."""
        self.valid_strftime_codes = {
            '%Y': '4-digit year (2024)',
            '%y': '2-digit year (24)',
            '%m': 'Month as number (01-12)',
            '%B': 'Full month name (January)',
            '%b': 'Short month name (Jan)',
            '%d': 'Day of month (01-31)',
            '%H': 'Hour 24-hour format (00-23)',
            '%I': 'Hour 12-hour format (01-12)',
            '%M': 'Minute (00-59)',
            '%S': 'Second (00-59)',
            '%A': 'Full weekday name (Monday)',
            '%a': 'Short weekday name (Mon)',
            '%j': 'Day of year (001-366)',
            '%U': 'Week number (00-53)',
            '%W': 'Week number (00-53)'
        }
        
        self.valid_custom_placeholders = {
            '{increment:03d}': '3-digit incremental number (001, 002, etc.)',
            '{increment:02d}': '2-digit incremental number (01, 02, etc.)',
            '{increment:04d}': '4-digit incremental number (0001, 0002, etc.)',
            '{increment}': 'Simple incremental number (1, 2, etc.)',
            '{city}': 'City name from GPS data',
            '{ext}': 'File extension (jpg, mp4, etc.)'
        }
        
        self.required_placeholders = ['{ext}']
        self.invalid_filename_chars = '<>:"|?*\\/\x00'
        self.reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                              'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                              'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    
    def validate_format_realtime(self, format_str: str) -> ValidationResult:
        """
        Perform comprehensive real-time validation of format string.
        
        Args:
            format_str: Format string to validate
            
        Returns:
            ValidationResult with detailed feedback
        """
        messages = []
        
        # Check for empty format
        if not format_str.strip():
            messages.append(ValidationMessage(
                ValidationSeverity.ERROR,
                "Format cannot be empty",
                "Try: %Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}"
            ))
            return ValidationResult(False, messages)
        
        # Check for required placeholders
        missing_required = self._check_required_placeholders(format_str)
        messages.extend(missing_required)
        
        # Check for invalid characters
        invalid_chars = self._check_invalid_characters(format_str)
        messages.extend(invalid_chars)
        
        # Check strftime codes
        strftime_issues = self._check_strftime_codes(format_str)
        messages.extend(strftime_issues)
        
        # Check custom placeholders
        placeholder_issues = self._check_custom_placeholders(format_str)
        messages.extend(placeholder_issues)
        
        # Check for unmatched braces
        brace_issues = self._check_unmatched_braces(format_str)
        messages.extend(brace_issues)
        
        # Check for reserved names
        reserved_issues = self._check_reserved_names(format_str)
        messages.extend(reserved_issues)
        
        # Generate example if format is valid
        example = None
        is_valid = not any(msg.severity == ValidationSeverity.ERROR for msg in messages)
        
        if is_valid:
            try:
                example = self._generate_example(format_str)
            except Exception as e:
                messages.append(ValidationMessage(
                    ValidationSeverity.ERROR,
                    f"Format generates invalid filename: {str(e)}"
                ))
                is_valid = False
        
        # Add helpful suggestions if format is valid but could be improved
        if is_valid and not messages:
            suggestions = self._get_improvement_suggestions(format_str)
            messages.extend(suggestions)
        
        return ValidationResult(is_valid, messages, example)
    
    def _check_required_placeholders(self, format_str: str) -> List[ValidationMessage]:
        """Check for missing required placeholders."""
        messages = []
        for placeholder in self.required_placeholders:
            if placeholder not in format_str:
                messages.append(ValidationMessage(
                    ValidationSeverity.ERROR,
                    f"Missing required placeholder: {placeholder}",
                    f"Add {placeholder} to include file extension"
                ))
        return messages
    
    def _check_invalid_characters(self, format_str: str) -> List[ValidationMessage]:
        """Check for invalid filename characters, excluding those inside placeholders."""
        messages = []
        in_placeholder = False
        
        for i, char in enumerate(format_str):
            # Track if we're inside a placeholder
            if char == '{':
                in_placeholder = True
            elif char == '}':
                in_placeholder = False
                continue
            
            # Skip validation inside placeholders (colons are valid there)
            if in_placeholder:
                continue
                
            if char in self.invalid_filename_chars:
                messages.append(ValidationMessage(
                    ValidationSeverity.ERROR,
                    f"Invalid character '{char}' at position {i}",
                    f"Replace '{char}' with '-' or '_'",
                    i
                ))
        
        return messages
    
    def _check_strftime_codes(self, format_str: str) -> List[ValidationMessage]:
        """Check strftime format codes for validity."""
        messages = []
        
        # Find all potential strftime codes (% followed by letters)
        # Check both single letter and common multi-letter attempts
        strftime_pattern = r'%(?:year|month|day|hour|minute|second|[a-zA-Z])'
        matches = re.finditer(strftime_pattern, format_str)
        
        for match in matches:
            code = match.group()
            if code not in self.valid_strftime_codes:
                suggestion = self._suggest_similar_strftime_code(code)
                messages.append(ValidationMessage(
                    ValidationSeverity.ERROR,
                    f"Invalid strftime code '{code}' at position {match.start()}",
                    suggestion,
                    match.start()
                ))
        
        return messages
    
    def _looks_like_strftime_attempt(self, code: str) -> bool:
        """Check if a code looks like an actual strftime attempt."""
        # Common invalid attempts that should be flagged
        invalid_attempts = ['%Z', '%X', '%Q']
        return code in invalid_attempts or len(code) == 2
    
    def _check_custom_placeholders(self, format_str: str) -> List[ValidationMessage]:
        """Check custom placeholders for validity."""
        messages = []
        
        # Find all custom placeholders
        placeholder_pattern = r'\{[^}]*\}'
        matches = re.finditer(placeholder_pattern, format_str)
        
        for match in matches:
            placeholder = match.group()
            if placeholder not in self.valid_custom_placeholders:
                # Check for common mistakes
                suggestion = self._suggest_placeholder_correction(placeholder)
                messages.append(ValidationMessage(
                    ValidationSeverity.ERROR,
                    f"Invalid placeholder '{placeholder}' at position {match.start()}",
                    suggestion,
                    match.start()
                ))
        
        return messages
    
    def _check_unmatched_braces(self, format_str: str) -> List[ValidationMessage]:
        """Check for unmatched braces in placeholders."""
        messages = []
        brace_stack = []
        
        for i, char in enumerate(format_str):
            if char == '{':
                brace_stack.append(i)
            elif char == '}':
                if not brace_stack:
                    messages.append(ValidationMessage(
                        ValidationSeverity.ERROR,
                        f"Unmatched closing brace '}}' at position {i}",
                        "Add opening brace '{{' before this position",
                        i
                    ))
                else:
                    brace_stack.pop()
        
        # Check for unmatched opening braces
        for pos in brace_stack:
            messages.append(ValidationMessage(
                ValidationSeverity.ERROR,
                f"Unmatched opening brace '{{{{' at position {pos}",
                "Add closing brace '}}' after placeholder",
                pos
            ))
        
        return messages
    
    def _check_reserved_names(self, format_str: str) -> List[ValidationMessage]:
        """Check if format might generate reserved Windows filenames."""
        messages = []
        
        # Generate a test example to check
        try:
            example = self._generate_example(format_str)
            base_name = example.split('.')[0].upper()
            
            if base_name in self.reserved_names:
                messages.append(ValidationMessage(
                    ValidationSeverity.WARNING,
                    f"Format may generate reserved filename '{base_name}'",
                    "Consider adding a prefix to avoid Windows reserved names"
                ))
        except:
            pass  # If we can't generate example, skip this check
        
        return messages
    
    def _suggest_similar_strftime_code(self, invalid_code: str) -> str:
        """Suggest similar valid strftime codes."""
        suggestions = {
            '%year': 'Use %Y for 4-digit year or %y for 2-digit year',
            '%month': 'Use %m for month number, %B for full name, or %b for short name',
            '%day': 'Use %d for day of month',
            '%hour': 'Use %H for 24-hour format or %I for 12-hour format',
            '%minute': 'Use %M for minute',
            '%second': 'Use %S for second',
            '%D': 'Use %d for day of month',
            '%T': 'Use %H:%M:%S for time',
            '%F': 'Use %Y-%m-%d for date'
        }
        
        return suggestions.get(invalid_code, f"Valid codes: {', '.join(list(self.valid_strftime_codes.keys())[:5])}")
    
    def _suggest_placeholder_correction(self, invalid_placeholder: str) -> str:
        """Suggest corrections for invalid placeholders."""
        lower_placeholder = invalid_placeholder.lower()
        
        suggestions = {
            '{inc}': 'Use {increment:03d} for 3-digit incremental number',
            '{number}': 'Use {increment:03d} for incremental numbering',
            '{count}': 'Use {increment:03d} for incremental numbering',
            '{extension}': 'Use {ext} for file extension',
            '{location}': 'Use {city} for city name from GPS',
            '{place}': 'Use {city} for city name from GPS',
            '{increment:3d}': 'Use {increment:03d} with leading zero',
            '{increment:3}': 'Use {increment:03d} for 3-digit format'
        }
        
        for pattern, suggestion in suggestions.items():
            if pattern in lower_placeholder:
                return suggestion
        
        return f"Valid placeholders: {', '.join(list(self.valid_custom_placeholders.keys())[:3])}"
    
    def _get_improvement_suggestions(self, format_str: str) -> List[ValidationMessage]:
        """Suggest improvements for valid but potentially problematic formats."""
        messages = []
        
        # Suggest adding increment if missing
        if '{increment' not in format_str:
            messages.append(ValidationMessage(
                ValidationSeverity.INFO,
                "Consider adding {increment:03d} for handling duplicate filenames",
                "Add {increment:03d} before {ext} for automatic numbering"
            ))
        
        # Suggest adding city if missing
        if '{city}' not in format_str and 'city' not in format_str.lower():
            messages.append(ValidationMessage(
                ValidationSeverity.INFO,
                "Consider adding {city} to include location information",
                "Add {city} to use GPS location data in filenames"
            ))
        
        # Check for potential length issues
        if len(format_str) > 100:
            messages.append(ValidationMessage(
                ValidationSeverity.WARNING,
                "Format string is very long and may cause filename length issues",
                "Consider shortening the format to avoid filesystem limits"
            ))
        
        return messages
    
    def _generate_example(self, format_str: str) -> str:
        """Generate example filename from format string."""
        sample_date = datetime(2024, 6, 30, 14, 32, 55)
        
        # Apply datetime formatting
        example = sample_date.strftime(format_str)
        
        # Replace custom placeholders
        replacements = {
            '{increment:03d}': '001',
            '{increment:02d}': '01',
            '{increment:04d}': '0001',
            '{increment}': '1',
            '{city}': 'NeoPsihiko',
            '{ext}': 'jpg'
        }
        
        for placeholder, value in replacements.items():
            example = example.replace(placeholder, value)
        
        return example
    
    def suggest_corrections(self, format_str: str) -> List[str]:
        """Get list of suggested format corrections."""
        validation = self.validate_format_realtime(format_str)
        return [msg.suggestion for msg in validation.messages if msg.suggestion]
    
    def get_format_suggestions(self) -> List[str]:
        """Get list of common format pattern suggestions."""
        return [
            "%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}",
            "%Y-%m-%d_%H-%M-%S_{city}_{increment:03d}.{ext}",
            "%Y%m%d_%H%M%S_{increment:03d}.{ext}",
            "%B_%d_%Y_{increment:03d}.{ext}",
            "%Y.%m.%d_{city}.{increment:03d}.{ext}",
            "%Y-%m-%d_{increment:04d}.{ext}",
            "%d.%m.%Y-%H.%M.%S.{ext}",
            "%Y%m%d_{city}_{increment:02d}.{ext}"
        ]


class FilenameGenerator:
    """Generates new filenames based on metadata and format patterns."""
    
    def __init__(self, format_pattern: str = "%Y.%m.%d-%H.%M.%S.{increment:03d}.{ext}"):
        """
        Initialize filename generator with format pattern.
        
        Args:
            format_pattern: Format string with placeholders for date, increment, city, ext
        """
        self.format_pattern = format_pattern
        self.validator = FormatValidator()
    
    def set_format(self, format_pattern: str) -> None:
        """Update the filename format pattern."""
        self.format_pattern = format_pattern
    
    def generate_filename(self, 
                         filepath: str, 
                         file_date: Optional[datetime], 
                         has_metadata: bool,
                         location: str, 
                         city: str, 
                         increment: int) -> Tuple[str, bool]:
        """
        Generate new filename based on metadata and format pattern.
        
        Args:
            filepath: Original file path
            file_date: Extracted creation date
            has_metadata: Whether file has valid metadata
            location: GPS location string
            city: City name from GPS
            increment: Incremental number for this file
            
        Returns:
            Tuple of (new_filename, has_metadata)
        """
        try:
            # Return original filename if no metadata available
            if not has_metadata or file_date is None:
                original_filename = os.path.basename(filepath)
                return original_filename, False
            
            # Get file extension without dot
            ext = os.path.splitext(filepath)[1][1:]
            
            # Clean city name for filename (remove spaces)
            city_formatted = city.replace(' ', '') if city else ''
            
            # Apply datetime formatting to the pattern
            new_name = file_date.strftime(self.format_pattern)
            
            # Replace custom placeholders
            replacements = {
                "{increment:03d}": f"{increment:03d}",
                "{city}": city_formatted,
                "{ext}": ext
            }
            
            for placeholder, value in replacements.items():
                new_name = new_name.replace(placeholder, value)
            
            return new_name, True
            
        except Exception as e:
            return f"Error: {str(e)}", False
    
    def generate_example(self, sample_date: Optional[datetime] = None) -> str:
        """
        Generate an example filename using the current format pattern.
        
        Args:
            sample_date: Date to use for example (defaults to a fixed sample date)
            
        Returns:
            Example filename string
        """
        try:
            if sample_date is None:
                sample_date = datetime(2024, 6, 30, 14, 32, 55)
            
            # Apply datetime formatting
            example = sample_date.strftime(self.format_pattern)
            
            # Replace placeholders with sample values
            example = example.replace("{increment:03d}", "001")
            example = example.replace("{city}", "NeoPsihiko")
            example = example.replace("{ext}", "jpg")
            
            return f"Example: {example}"
            
        except Exception:
            return "Example: Invalid format"
    
    def validate_format(self, format_pattern: str) -> Tuple[bool, str]:
        """
        Validate a filename format pattern (legacy method for backward compatibility).
        
        Args:
            format_pattern: Format string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        validation = self.validator.validate_format_realtime(format_pattern)
        if validation.is_valid:
            return True, ""
        else:
            # Return first error message
            error_msg = validation.errors[0].message if validation.errors else "Invalid format"
            return False, error_msg
    
    def validate_format_detailed(self, format_pattern: str) -> ValidationResult:
        """
        Perform detailed validation with comprehensive feedback.
        
        Args:
            format_pattern: Format string to validate
            
        Returns:
            ValidationResult with detailed messages and suggestions
        """
        return self.validator.validate_format_realtime(format_pattern)
    
    def get_available_placeholders(self) -> dict:
        """
        Get dictionary of available placeholders and their descriptions.
        
        Returns:
            Dictionary mapping placeholder to description
        """
        # Combine strftime codes and custom placeholders
        placeholders = {}
        placeholders.update(self.validator.valid_strftime_codes)
        placeholders.update(self.validator.valid_custom_placeholders)
        return placeholders
    
    def get_format_suggestions(self) -> List[str]:
        """
        Get list of suggested format patterns.
        
        Returns:
            List of common format pattern suggestions
        """
        return self.validator.get_format_suggestions()
    
    def suggest_format_corrections(self, format_pattern: str) -> List[str]:
        """
        Get suggestions for correcting an invalid format.
        
        Args:
            format_pattern: Format string to analyze
            
        Returns:
            List of correction suggestions
        """
        return self.validator.suggest_corrections(format_pattern)
    
    def generate_batch_filenames(self, 
                               file_data_list: list,
                               resolve_duplicates: bool = True) -> list:
        """
        Generate filenames for a batch of files with optional duplicate resolution.
        
        Args:
            file_data_list: List of tuples (filepath, file_date, has_metadata, location, city, increment)
            resolve_duplicates: Whether to resolve duplicate names
            
        Returns:
            List of tuples (original_name, generated_name)
        """
        generated_mappings = []
        
        for filepath, file_date, has_metadata, location, city, increment in file_data_list:
            original_name = os.path.basename(filepath)
            generated_name, _ = self.generate_filename(
                filepath, file_date, has_metadata, location, city, increment
            )
            generated_mappings.append((original_name, generated_name))
        
        if resolve_duplicates:
            # Import here to avoid circular imports
            from file_operations import DuplicateResolver
            resolver = DuplicateResolver()
            return resolver.resolve_duplicates(generated_mappings)
        
        return generated_mappings