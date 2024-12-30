import pytest
from youtube_handler import YoutubeHandler
from transcript_processor import TranscriptProcessor
from markdown_generator import MarkdownGenerator
import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_path = str(Path(__file__).parent.parent)
sys.path.append(src_path)

@pytest.fixture
def youtube_handler():
    return YoutubeHandler()

@pytest.fixture
def transcript_processor():
    return TranscriptProcessor(batch_size=1, use_gpu=False)

@pytest.fixture
def markdown_generator():
    return MarkdownGenerator()

@pytest.fixture
def sample_video():
    return {
        'title': 'Test Video',
        'url': 'https://www.youtube.com/watch?v=123456',
        'video_id': '123456'
    }

@pytest.fixture
def sample_transcript():
    return 'This is a test transcript for the video content.' 