import pytest
import os
from main import parse_arguments
from unittest.mock import patch, MagicMock

def test_env_defaults(monkeypatch):
    # Create a temporary environment without any variables
    clean_env = {}
    monkeypatch.setattr(os, 'environ', clean_env)
    
    # Mock the entire dotenv module
    class MockDotEnv:
        def load_dotenv(self, *args, **kwargs):
            return {}
    monkeypatch.setattr('main.load_dotenv', MockDotEnv().load_dotenv)
    
    # Mock sys.argv to avoid command line arguments
    monkeypatch.setattr('sys.argv', ['script.py'])
    
    # Mock os.path.exists to return False for .env file
    monkeypatch.setattr('os.path.exists', lambda x: False)
    
    # Mock SystemInfo to return consistent values
    mock_settings = {
        'num_gpus': 0,
        'num_cpus': 1,
        'num_threads': 1
    }
    
    with patch('utils.SystemInfo.get_optimal_settings', return_value=mock_settings):
        args = parse_arguments()
    
    # Check that default values are set correctly
    assert args.videos is None
    assert args.categories is None
    assert args.batch_size == 1
    assert args.num_gpus == 0
    assert args.num_cpus == 1
    assert args.model == 'llama3.2'
    assert args.threads == 1
    assert not args.verbose

def test_env_boolean_parsing(monkeypatch):
    test_cases = [
        ('true', True),
        ('True', True),
        ('1', True),
        ('yes', True),
        ('false', False),
        ('False', False),
        ('0', False),
        ('no', False),
        ('', False),
    ]
    
    for env_value, expected in test_cases:
        monkeypatch.setenv('VERBOSE', env_value)
        args = parse_arguments()
        assert args.verbose == expected

def test_invalid_env_values(monkeypatch):
    monkeypatch.setenv('NUM_GPUS', 'invalid')
    with pytest.raises(ValueError):
        parse_arguments() 

def test_env_playlist_url(monkeypatch):
    test_url = 'https://example.com/playlist'
    
    # Test with command line argument
    monkeypatch.setattr('sys.argv', ['script.py', '--playlist-url', test_url])
    args = parse_arguments()
    assert args.playlist_url == test_url 