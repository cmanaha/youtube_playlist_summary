import pytest
from main import parse_arguments, TimingStats
import os

def test_env_variable_parsing(monkeypatch):
    # Set environment variables
    monkeypatch.setenv('VIDEOS', '10')
    monkeypatch.setenv('NUM_GPUS', '2')
    monkeypatch.setenv('NUM_CPUS', '8')
    monkeypatch.setenv('VERBOSE', 'true')
    
    args = parse_arguments()
    assert args.videos == 10
    assert args.num_gpus == 2
    assert args.num_cpus == 8
    assert args.verbose == True

def test_timing_stats():
    stats = TimingStats()
    stats.add_timing("test_op", 1.5)
    stats.add_timing("test_op", 2.5)
    
    assert len(stats.timings["test_op"]) == 2
    assert sum(stats.timings["test_op"]) == 4.0

def test_command_line_override(monkeypatch):
    # Set env var
    monkeypatch.setenv('VIDEOS', '10')
    
    # Mock command line args
    monkeypatch.setattr('sys.argv', ['script.py', '--videos', '5'])
    
    args = parse_arguments()
    assert args.videos == 5  # Command line should override env var 