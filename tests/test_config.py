import os
import unittest
from unittest.mock import patch
import importlib
import config

class TestConfig(unittest.TestCase):
    def setUp(self):
        # Store original environment variables
        self.original_env = dict(os.environ)

    def tearDown(self):
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)
        # Reload config module
        importlib.reload(config)

    def test_validate_config_with_vars(self):
        """Test config validation with all required variables."""
        test_vars = {
            'AZURE_SPEECH_KEY': 'test_key',
            'AZURE_SPEECH_REGION': 'test_region',
            'AZURE_OPENAI_KEY': 'test_key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com',
            'AZURE_OPENAI_DEPLOYMENT': 'test_deployment',
            'EMAIL_USER': 'test@example.com',
            'EMAIL_PASSWORD': 'test_password',
            'EMAIL_SMTP_SERVER': 'smtp.test.com',
            'EMAIL_SMTP_PORT': '587'
        }
        
        with patch.dict(os.environ, test_vars, clear=True):
            importlib.reload(config)
            self.assertTrue(config.validate_config())

    def test_validate_config_missing_vars(self):
        """Test config validation with missing variables."""
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(config)
            self.assertFalse(config.validate_config())

    def test_openai_endpoint_cleanup(self):
        """Test OpenAI endpoint URL cleanup."""
        test_endpoints = [
            ('https://test.openai.azure.com/', 'https://test.openai.azure.com'),
            ('https://test.openai.azure.com/openai', 'https://test.openai.azure.com'),
            ('https://test.openai.azure.com/openai/', 'https://test.openai.azure.com')
        ]

        for input_endpoint, expected_endpoint in test_endpoints:
            with patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT': input_endpoint}, clear=True):
                importlib.reload(config)
                self.assertEqual(config.AZURE_OPENAI_ENDPOINT, expected_endpoint)

if __name__ == '__main__':
    unittest.main() 