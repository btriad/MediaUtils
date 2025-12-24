"""
Unit tests for error recovery system

Tests retry mechanisms, graceful degradation, and error handling scenarios.
Requirements: 6.1, 6.2, 6.3
"""

import unittest
import logging
import time
import subprocess
from unittest.mock import Mock, patch, MagicMock
import json

from error_recovery import (
    ErrorRecovery, 
    ErrorType, 
    RecoveryResult, 
    with_retry, 
    safe_execute
)


class TestErrorRecovery(unittest.TestCase):
    """Test cases for ErrorRecovery class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.recovery = ErrorRecovery(logger=self.logger, max_retries=3)
    
    def test_retry_with_backoff_success_first_attempt(self):
        """Test successful function execution on first attempt"""
        # Arrange
        mock_func = Mock(return_value="success")
        
        # Act
        result = self.recovery.retry_with_backoff(mock_func, "arg1", key="value")
        
        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.result, "success")
        self.assertEqual(result.attempts, 1)
        self.assertEqual(result.recovery_method, "retry_with_backoff")
        mock_func.assert_called_once_with("arg1", key="value")
    
    def test_retry_with_backoff_success_after_retries(self):
        """Test successful function execution after retries"""
        # Arrange
        mock_func = Mock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])
        
        with patch('time.sleep') as mock_sleep:
            # Act
            result = self.recovery.retry_with_backoff(mock_func)
            
            # Assert
            self.assertTrue(result.success)
            self.assertEqual(result.result, "success")
            self.assertEqual(result.attempts, 3)
            self.assertEqual(mock_func.call_count, 3)
            
            # Check exponential backoff sleep calls
            expected_sleep_calls = [unittest.mock.call(1), unittest.mock.call(2)]
            mock_sleep.assert_has_calls(expected_sleep_calls)
    
    def test_retry_with_backoff_all_attempts_fail(self):
        """Test function that fails all retry attempts"""
        # Arrange
        error = Exception("persistent failure")
        mock_func = Mock(side_effect=error)
        
        with patch('time.sleep'):
            # Act
            result = self.recovery.retry_with_backoff(mock_func)
            
            # Assert
            self.assertFalse(result.success)
            self.assertEqual(result.error, error)
            self.assertEqual(result.attempts, 3)
            self.assertEqual(mock_func.call_count, 3)
    
    def test_handle_network_error_with_cached_data(self):
        """Test network error handling with cached data fallback"""
        # Arrange
        error = ConnectionError("Network unavailable")
        cached_data = "cached_city_name"
        
        # Act
        result = self.recovery.handle_network_error(error, "GPS lookup", cached_data)
        
        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.result, cached_data)
        self.assertEqual(result.recovery_method, "cached_fallback")
        self.logger.error.assert_called_once()
        self.logger.info.assert_called_once()
    
    def test_handle_network_error_without_cached_data(self):
        """Test network error handling without cached data"""
        # Arrange
        error = ConnectionError("Network unavailable")
        
        # Act
        result = self.recovery.handle_network_error(error, "GPS lookup")
        
        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.result, "")
        self.assertEqual(result.recovery_method, "graceful_degradation")
        self.logger.error.assert_called_once()
        self.logger.info.assert_called_once()
    
    @patch('os.path.exists')
    @patch('os.stat')
    def test_handle_file_permission_error(self, mock_stat, mock_exists):
        """Test file permission error handling"""
        # Arrange
        filepath = "/test/file.jpg"
        mock_exists.return_value = True
        mock_stat.return_value = Mock(st_size=1024)
        
        # Act
        result = self.recovery.handle_file_permission_error(filepath, "read")
        
        # Assert
        self.assertFalse(result.success)
        self.assertIsInstance(result.error, PermissionError)
        self.assertEqual(result.recovery_method, "log_and_skip")
        self.logger.error.assert_called_once()
    
    @patch('os.path.exists')
    @patch('os.stat')
    def test_handle_corrupted_file_error(self, mock_stat, mock_exists):
        """Test corrupted file error handling"""
        # Arrange
        filepath = "/test/corrupted.jpg"
        error = ValueError("Invalid EXIF data")
        mock_exists.return_value = True
        mock_stat.return_value = Mock(st_size=2048)
        
        # Act
        result = self.recovery.handle_corrupted_file_error(filepath, error)
        
        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.error, error)
        self.assertEqual(result.recovery_method, "log_and_continue")
        self.logger.error.assert_called_once()
    
    @patch('subprocess.run')
    def test_check_ffprobe_availability_success(self, mock_run):
        """Test ffprobe availability check when ffprobe is available"""
        # Arrange
        mock_run.return_value = Mock(returncode=0)
        
        # Act
        result = self.recovery.check_ffprobe_availability()
        
        # Assert
        self.assertTrue(result)
        self.assertTrue(self.recovery.ffprobe_available)
        mock_run.assert_called_once_with(
            ['ffprobe', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
    
    @patch('subprocess.run')
    def test_check_ffprobe_availability_not_found(self, mock_run):
        """Test ffprobe availability check when ffprobe is not found"""
        # Arrange
        mock_run.side_effect = FileNotFoundError("ffprobe not found")
        
        # Act
        result = self.recovery.check_ffprobe_availability()
        
        # Assert
        self.assertFalse(result)
        self.assertFalse(self.recovery.ffprobe_available)
        self.logger.warning.assert_called_once()
    
    @patch('subprocess.run')
    def test_check_ffprobe_availability_timeout(self, mock_run):
        """Test ffprobe availability check timeout"""
        # Arrange
        mock_run.side_effect = subprocess.TimeoutExpired(['ffprobe', '-version'], 5)
        
        # Act
        result = self.recovery.check_ffprobe_availability()
        
        # Assert
        self.assertFalse(result)
        self.assertFalse(self.recovery.ffprobe_available)
        self.logger.warning.assert_called_once()
    
    def test_check_ffprobe_availability_cached(self):
        """Test that ffprobe availability is cached after first check"""
        # Arrange
        self.recovery.ffprobe_available = True
        
        with patch('subprocess.run') as mock_run:
            # Act
            result = self.recovery.check_ffprobe_availability()
            
            # Assert
            self.assertTrue(result)
            mock_run.assert_not_called()  # Should use cached value
    
    def test_handle_ffprobe_unavailable(self):
        """Test handling when ffprobe is unavailable"""
        # Arrange
        filepath = "/test/video.mp4"
        self.recovery.ffprobe_available = False
        
        with patch.object(self.recovery, 'check_ffprobe_availability', return_value=False):
            # Act
            result = self.recovery.handle_ffprobe_unavailable(filepath)
            
            # Assert
            self.assertFalse(result.success)
            self.assertIsInstance(result.error, FileNotFoundError)
            self.assertEqual(result.recovery_method, "image_only_processing")
            self.logger.warning.assert_called_once()
    
    def test_handle_gps_api_error_with_json_response(self):
        """Test GPS API error handling with JSON response"""
        # Arrange
        error = ValueError("Invalid coordinates")
        api_response = '{"error": "Invalid request", "code": 400}'
        
        # Act
        result = self.recovery.handle_gps_api_error(error, api_response)
        
        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.result, "")
        self.assertEqual(result.recovery_method, "continue_without_city")
        self.logger.error.assert_called_once()
        self.logger.debug.assert_called()
    
    def test_handle_gps_api_error_with_invalid_json(self):
        """Test GPS API error handling with invalid JSON response"""
        # Arrange
        error = ValueError("Invalid coordinates")
        api_response = "Invalid response format"
        
        # Act
        result = self.recovery.handle_gps_api_error(error, api_response)
        
        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.result, "")
        self.assertEqual(result.recovery_method, "continue_without_city")
        self.logger.error.assert_called_once()
    
    def test_log_and_continue(self):
        """Test log and continue error handling"""
        # Arrange
        error = RuntimeError("Test error")
        context = "file processing"
        filepath = "/test/file.jpg"
        
        # Act
        result = self.recovery.log_and_continue(error, context, filepath)
        
        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.error, error)
        self.assertEqual(result.recovery_method, "log_and_continue")
        self.logger.error.assert_called_once()
    
    def test_get_recovery_stats(self):
        """Test recovery statistics retrieval"""
        # Act
        stats = self.recovery.get_recovery_stats()
        
        # Assert
        self.assertIsInstance(stats, dict)
        self.assertIn("total_recoveries", stats)
        self.assertIn("successful_recoveries", stats)
        self.assertIn("failed_recoveries", stats)


class TestRetryDecorator(unittest.TestCase):
    """Test cases for retry decorator"""
    
    def test_with_retry_decorator_success(self):
        """Test retry decorator with successful function"""
        # Arrange
        @with_retry(max_retries=2)
        def test_func(value):
            return value * 2
        
        # Act
        result = test_func(5)
        
        # Assert
        self.assertEqual(result, 10)
    
    def test_with_retry_decorator_failure(self):
        """Test retry decorator with failing function"""
        # Arrange
        @with_retry(max_retries=2)
        def test_func():
            raise ValueError("Test error")
        
        # Act & Assert
        with self.assertRaises(ValueError):
            test_func()


class TestSafeExecute(unittest.TestCase):
    """Test cases for safe_execute function"""
    
    def test_safe_execute_success(self):
        """Test safe_execute with successful function"""
        # Arrange
        def test_func(x, y):
            return x + y
        
        # Act
        result = safe_execute(test_func, 3, 4)
        
        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.result, 7)
        self.assertEqual(result.attempts, 1)
    
    def test_safe_execute_failure(self):
        """Test safe_execute with failing function"""
        # Arrange
        def test_func():
            raise RuntimeError("Test error")
        
        logger = Mock(spec=logging.Logger)
        
        # Act
        result = safe_execute(test_func, logger=logger)
        
        # Assert
        self.assertFalse(result.success)
        self.assertIsInstance(result.error, RuntimeError)
        logger.error.assert_called_once()


class TestGracefulDegradationScenarios(unittest.TestCase):
    """Test graceful degradation scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.recovery = ErrorRecovery(logger=self.logger)
    
    def test_network_failure_with_cache_fallback(self):
        """Test network failure scenario with cache fallback"""
        # Arrange
        def failing_network_call():
            raise ConnectionError("Network unreachable")
        
        cached_city = "San Francisco"
        
        # Act
        network_result = self.recovery.retry_with_backoff(failing_network_call)
        fallback_result = self.recovery.handle_network_error(
            network_result.error, 
            "GPS lookup", 
            cached_city
        )
        
        # Assert
        self.assertFalse(network_result.success)
        self.assertTrue(fallback_result.success)
        self.assertEqual(fallback_result.result, cached_city)
        self.assertEqual(fallback_result.recovery_method, "cached_fallback")
    
    def test_complete_network_failure_graceful_degradation(self):
        """Test complete network failure with graceful degradation"""
        # Arrange
        def failing_network_call():
            raise ConnectionError("Network unreachable")
        
        # Act
        network_result = self.recovery.retry_with_backoff(failing_network_call)
        fallback_result = self.recovery.handle_network_error(
            network_result.error, 
            "GPS lookup"
        )
        
        # Assert
        self.assertFalse(network_result.success)
        self.assertTrue(fallback_result.success)
        self.assertEqual(fallback_result.result, "")
        self.assertEqual(fallback_result.recovery_method, "graceful_degradation")
    
    @patch('subprocess.run')
    def test_ffprobe_unavailable_graceful_degradation(self, mock_run):
        """Test ffprobe unavailable with graceful degradation"""
        # Arrange
        mock_run.side_effect = FileNotFoundError("ffprobe not found")
        filepath = "/test/video.mp4"
        
        # Act
        result = self.recovery.handle_ffprobe_unavailable(filepath)
        
        # Assert
        self.assertFalse(result.success)
        self.assertEqual(result.recovery_method, "image_only_processing")
        # Should have two warning calls: one for ffprobe not found, one for skipping video metadata
        self.assertEqual(self.logger.warning.call_count, 2)
    
    def test_multiple_error_types_handling(self):
        """Test handling multiple types of errors in sequence"""
        # Arrange
        errors = [
            (ConnectionError("Network error"), "network"),
            (PermissionError("Permission denied"), "file_permission"),
            (ValueError("Corrupted data"), "corrupted_file")
        ]
        
        results = []
        
        # Act
        for error, error_type in errors:
            if error_type == "network":
                result = self.recovery.handle_network_error(error, "test context")
            elif error_type == "file_permission":
                result = self.recovery.handle_file_permission_error("/test/file", "read")
            else:
                result = self.recovery.handle_corrupted_file_error("/test/file", error)
            
            results.append(result)
        
        # Assert
        # Network error should succeed with graceful degradation
        self.assertTrue(results[0].success)
        self.assertEqual(results[0].recovery_method, "graceful_degradation")
        
        # Permission error should fail but be handled
        self.assertFalse(results[1].success)
        self.assertEqual(results[1].recovery_method, "log_and_skip")
        
        # Corrupted file should fail but allow continuation
        self.assertFalse(results[2].success)
        self.assertEqual(results[2].recovery_method, "log_and_continue")


if __name__ == '__main__':
    unittest.main()