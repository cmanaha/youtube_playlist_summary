# © 2024 Carlos Manzanedo Rueda
# MIT License

import pytest
from unittest.mock import patch
import os

# Create mock class outside the test function
class MockSystemInfo:
    @staticmethod
    def get_optimal_settings(verbose=False):
        return {
            'num_gpus': 0,
            'num_cpus': 4,
            'num_threads': 4
        }
    
    @staticmethod
    def get_gpu_count(verbose=False):
        return 0
    
    @staticmethod
    def get_cpu_count():
        return 4

@patch('src.utils.SystemInfo', MockSystemInfo)
@patch('src.utils.SystemInfo.get_cpu_count', return_value=4)
@patch('src.utils.SystemInfo.get_gpu_count', return_value=0)
def test_parse_arguments_defaults(mock_system_info, mock_get_gpu_count):
    """Test default argument parsing with mocked system info."""
    with patch('sys.argv', ['script.py']), \
         patch.dict('os.environ', {}, clear=True), \
         patch('dotenv.load_dotenv', return_value=None), \
         patch('os.path.exists', return_value=False):
        # Import parse_arguments here, after the mock is in place
        from src.main import parse_arguments
        args = parse_arguments()
        assert args.playlist_url is None
        assert args.videos is None
        assert args.batch_size == 1
        assert args.model == 'llama3.2'
        assert not args.verbose
        assert args.output is None

def test_parse_arguments_with_values():
    test_args = [
        'script.py',
        '--playlist-url', 'https://youtube.com/playlist?list=123',
        '--videos', '5',
        '--batch-size', '2',
        '--num-gpus', '1',
        '--num-cpus', '8',
        '--model', 'claude',
        '--threads', '6',
        '--verbose',
        '-o', 'output.md'
    ]
    
    with patch('sys.argv', test_args):
        # Import parse_arguments here
        from src.main import parse_arguments
        args = parse_arguments()
        assert args.playlist_url == 'https://youtube.com/playlist?list=123'
        assert args.videos == 5
        assert args.batch_size == 2
        assert args.num_gpus == 1
        assert args.num_cpus == 8
        assert args.model == 'claude'
        assert args.threads == 6
        assert args.verbose
        assert args.output == 'output.md'

def test_parse_arguments_from_env():
    env_vars = {
        'PLAYLIST_URL': 'https://youtube.com/playlist?list=123',
        'VIDEOS': '5',
        'BATCH_SIZE': '2',
        'NUM_GPUS': '1',
        'NUM_CPUS': '8',
        'MODEL': 'claude',
        'THREADS': '6',
        'VERBOSE': 'true',
        'OUTPUT': 'output.md'
    }
    
    with patch.dict(os.environ, env_vars), patch('sys.argv', ['script.py']):
        # Import parse_arguments here
        from src.main import parse_arguments
        args = parse_arguments()
        assert args.playlist_url == 'https://youtube.com/playlist?list=123'
        assert args.videos == 5
        assert args.batch_size == 2
        assert args.num_gpus == 1
        assert args.num_cpus == 8
        assert args.model == 'claude'
        assert args.threads == 6
        assert args.verbose
        assert args.output == 'output.md' 