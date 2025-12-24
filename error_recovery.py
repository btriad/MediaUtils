"""
Error Recovery System for Media File Renamer

This module provides comprehensive error recovery mechanisms including:
- Retry logic with exponential backoff for network requests
- Graceful handling of ffprobe availability issues
- File permission error handling
- Corrupted file error handling
- Network timeout recovery
- GPS API error handling

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
"""

import asyncio
import logging
import time
import subprocess
import os
from typing import Callable, Any, Optional, Dict, List
from enum import Enum
from dataclasses import dataclass
import json


class ErrorType(Enum):
    """Types of errors that can be recovered from"""
    NETWORK_ERROR = "network_error"
    FILE_PERMISSION_ERROR = "file_permission_error"
    CORRUPTED_FILE_ERROR = "corrupted_file_error"
    FFPROBE_UNAVAILABLE = "ffprobe_unavailable"
    GPS_API_ERROR = "gps_api_error"
    TIMEOUT_ERROR = "timeout_error"


@dataclass
class RecoveryResult:
    """Result of an error recovery attempt"""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    attempts: int = 0
    recovery_method: Optional[str] = None


class ErrorRecovery:
    """
    Comprehensive error recovery system with retry mechanisms and graceful degradation
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None, max_retries: int = 3):
        """
        Initialize error recovery system
        
        Args:
            logger: Logger instance for recording recovery attempts
            max_retries: Maximum number of retry attempts for recoverable errors
        """
        self.logger = logger or logging.getLogger(__name__)
        self.max_retries = max_retries
        self.ffprobe_available = None  # Cache ffprobe availability check
        
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> RecoveryResult:
        """
        Retry a function with exponential backoff
        
        Args:
            func: Function to retry
            *args: Arguments to pass to function
            **kwargs: Keyword arguments to pass to function
            
        Returns:
            RecoveryResult with success status and result or error
            
        Requirements: 6.2 - Retry up to 3 times with exponential backoff
        """
        last_error = None
        
        func_name = getattr(func, '__name__', 'function')
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Attempting {func_name}, attempt {attempt + 1}/{self.max_retries}")
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(f"Successfully recovered {func_name} after {attempt + 1} attempts")
                
                return RecoveryResult(
                    success=True,
                    result=result,
                    attempts=attempt + 1,
                    recovery_method="retry_with_backoff"
                )
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt + 1} failed for {func_name}: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    sleep_time = 2 ** attempt
                    self.logger.debug(f"Waiting {sleep_time}s before retry")
                    time.sleep(sleep_time)
        
        self.logger.error(f"All {self.max_retries} attempts failed for {func_name}: {str(last_error)}")
        return RecoveryResult(
            success=False,
            error=last_error,
            attempts=self.max_retries,
            recovery_method="retry_with_backoff"
        )
    
    def handle_network_error(self, error: Exception, context: str, cached_data: Any = None) -> RecoveryResult:
        """
        Handle network errors with fallback to cached data
        
        Args:
            error: The network error that occurred
            context: Context description for logging
            cached_data: Optional cached data to use as fallback
            
        Returns:
            RecoveryResult with fallback data or graceful degradation
            
        Requirements: 6.2, 6.3 - Use cached data if available or continue without city information
        """
        self.logger.error(f"Network error in {context}: {str(error)}")
        
        if cached_data is not None:
            self.logger.info(f"Using cached data for {context}")
            return RecoveryResult(
                success=True,
                result=cached_data,
                attempts=1,
                recovery_method="cached_fallback"
            )
        
        self.logger.info(f"No cached data available for {context}, continuing without network data")
        return RecoveryResult(
            success=True,
            result="",  # Empty string for missing city data
            attempts=1,
            recovery_method="graceful_degradation"
        )
    
    def handle_file_permission_error(self, filepath: str, operation: str = "read") -> RecoveryResult:
        """
        Handle file permission errors
        
        Args:
            filepath: Path to the file with permission issues
            operation: Type of operation that failed (read, write, etc.)
            
        Returns:
            RecoveryResult indicating how to proceed
            
        Requirements: 6.4 - Log error and mark file as no metadata
        """
        self.logger.error(f"Permission denied for {operation} operation on file: {filepath}")
        
        # Check if file exists and get some basic info
        try:
            if os.path.exists(filepath):
                stat_info = os.stat(filepath)
                self.logger.debug(f"File exists, size: {stat_info.st_size} bytes")
            else:
                self.logger.error(f"File does not exist: {filepath}")
        except Exception as e:
            self.logger.debug(f"Could not get file info: {str(e)}")
        
        return RecoveryResult(
            success=False,
            error=PermissionError(f"Permission denied: {filepath}"),
            attempts=1,
            recovery_method="log_and_skip"
        )
    
    def handle_corrupted_file_error(self, filepath: str, error: Exception) -> RecoveryResult:
        """
        Handle corrupted file errors
        
        Args:
            filepath: Path to the corrupted file
            error: The error that occurred when processing the file
            
        Returns:
            RecoveryResult indicating to continue processing other files
            
        Requirements: 6.5 - Log error and continue processing other files
        """
        self.logger.error(f"Corrupted file detected: {filepath} - {str(error)}")
        
        # Try to get basic file info for debugging
        try:
            if os.path.exists(filepath):
                stat_info = os.stat(filepath)
                self.logger.debug(f"Corrupted file size: {stat_info.st_size} bytes")
        except Exception as e:
            self.logger.debug(f"Could not get corrupted file info: {str(e)}")
        
        return RecoveryResult(
            success=False,
            error=error,
            attempts=1,
            recovery_method="log_and_continue"
        )
    
    def check_ffprobe_availability(self) -> bool:
        """
        Check if ffprobe is available on the system
        
        Returns:
            True if ffprobe is available, False otherwise
            
        Requirements: 6.1 - Check ffprobe availability and log if not available
        """
        if self.ffprobe_available is not None:
            return self.ffprobe_available
        
        try:
            # Try to run ffprobe with version flag
            result = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.logger.info("ffprobe is available")
                self.ffprobe_available = True
                return True
            else:
                self.logger.warning("ffprobe command failed")
                self.ffprobe_available = False
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.warning("ffprobe availability check timed out")
            self.ffprobe_available = False
            return False
        except FileNotFoundError:
            self.logger.warning("ffprobe not found in system PATH")
            self.ffprobe_available = False
            return False
        except Exception as e:
            self.logger.error(f"Error checking ffprobe availability: {str(e)}")
            self.ffprobe_available = False
            return False
    
    def handle_ffprobe_unavailable(self, filepath: str) -> RecoveryResult:
        """
        Handle cases where ffprobe is not available
        
        Args:
            filepath: Path to file that needs ffprobe processing
            
        Returns:
            RecoveryResult indicating to continue with image-only processing
            
        Requirements: 6.1 - Log issue and continue processing other files
        """
        if not self.check_ffprobe_availability():
            self.logger.warning(f"ffprobe unavailable, skipping video metadata for: {filepath}")
            return RecoveryResult(
                success=False,
                error=FileNotFoundError("ffprobe not available"),
                attempts=1,
                recovery_method="image_only_processing"
            )
        
        return RecoveryResult(success=True, result=True, attempts=1)
    
    def handle_gps_api_error(self, error: Exception, api_response: str = "") -> RecoveryResult:
        """
        Handle GPS API errors and invalid responses
        
        Args:
            error: The API error that occurred
            api_response: The invalid API response (if any)
            
        Returns:
            RecoveryResult indicating to continue without city information
            
        Requirements: 6.6 - Log response and continue without city information
        """
        self.logger.error(f"GPS API error: {str(error)}")
        
        if api_response:
            self.logger.debug(f"Invalid API response: {api_response}")
            
            # Try to parse response for debugging
            try:
                if api_response.strip().startswith('{'):
                    parsed = json.loads(api_response)
                    self.logger.debug(f"Parsed API response: {parsed}")
            except json.JSONDecodeError:
                self.logger.debug("API response is not valid JSON")
        
        return RecoveryResult(
            success=True,
            result="",  # Empty city name
            attempts=1,
            recovery_method="continue_without_city"
        )
    
    def log_and_continue(self, error: Exception, context: str, filepath: str = "") -> RecoveryResult:
        """
        Log an error and indicate processing should continue
        
        Args:
            error: The error that occurred
            context: Context description for the error
            filepath: Optional file path related to the error
            
        Returns:
            RecoveryResult indicating to continue processing
        """
        error_msg = f"Error in {context}"
        if filepath:
            error_msg += f" for file {filepath}"
        error_msg += f": {str(error)}"
        
        self.logger.error(error_msg)
        
        return RecoveryResult(
            success=False,
            error=error,
            attempts=1,
            recovery_method="log_and_continue"
        )
    
    def get_recovery_stats(self) -> Dict[str, int]:
        """
        Get statistics about recovery operations (placeholder for future implementation)
        
        Returns:
            Dictionary with recovery statistics
        """
        # This could be enhanced to track recovery statistics
        return {
            "total_recoveries": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0
        }


# Convenience functions for common error recovery patterns

def with_retry(max_retries: int = 3, logger: Optional[logging.Logger] = None):
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        logger: Logger instance for recording attempts
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            recovery = ErrorRecovery(logger=logger, max_retries=max_retries)
            result = recovery.retry_with_backoff(func, *args, **kwargs)
            
            if result.success:
                return result.result
            else:
                raise result.error
        
        return wrapper
    return decorator


def safe_execute(func: Callable, *args, logger: Optional[logging.Logger] = None, **kwargs) -> RecoveryResult:
    """
    Safely execute a function with error recovery
    
    Args:
        func: Function to execute
        *args: Arguments to pass to function
        logger: Logger for recording errors
        **kwargs: Keyword arguments to pass to function
        
    Returns:
        RecoveryResult with execution result or error information
    """
    recovery = ErrorRecovery(logger=logger)
    
    try:
        result = func(*args, **kwargs)
        return RecoveryResult(success=True, result=result, attempts=1)
    except Exception as e:
        func_name = getattr(func, '__name__', 'function')
        return recovery.log_and_continue(e, func_name)