import pytest
from src.youtube_handler import YoutubeHandler
from unittest.mock import patch, MagicMock

@pytest.fixture
def youtube_handler():
    return YoutubeHandler(verbose=True)  # Remove saved_transcripts parameter

def test_youtube_handler_initialization():
    handler = YoutubeHandler(verbose=True)
    assert handler.verbose is True
    assert handler.videos == []
    assert handler.ydl_opts == {
        'quiet': True,
        'extract_flat': True,
        'force_generic_extractor': True
    }

@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/playlist?list=123", True),
    ("https://www.youtube.com/watch?v=123&list=456", True),
    ("https://youtu.be/123?list=789", True),
    ("https://youtube.com/watch?v=123", False),
    ("https://invalid.com/playlist", False),
])
def test_validate_youtube_playlist_url(youtube_handler, url, expected):
    assert youtube_handler._validate_youtube_playlist_url(url) == expected

@patch('yt_dlp.YoutubeDL')
def test_get_playlist_videos_success(mock_ytdl, youtube_handler):
    # Mock the YoutubeDL response
    mock_result = {
        'title': 'Test Playlist',
        'entries': [
            {'id': '123', 'title': 'Video 1', 'description': 'Desc 1'},
            {'id': '456', 'title': 'Video 2', 'description': 'Desc 2'}
        ]
    }
    mock_ytdl.return_value.__enter__.return_value.extract_info.return_value = mock_result

    videos, playlist_title = youtube_handler.get_playlist_videos('https://www.youtube.com/playlist?list=123')
    
    assert playlist_title == 'Test Playlist'
    assert len(videos) == 2
    assert videos[0]['video_id'] == '123'
    assert videos[1]['video_id'] == '456'

@patch('src.youtube_handler.YouTubeTranscriptApi')
def test_get_transcript_success(mock_transcript_api, youtube_handler):
    # Create mock transcript and list
    mock_transcript = MagicMock()
    mock_transcript.fetch.return_value = [{'text': 'Hello'}, {'text': 'World'}]
    
    mock_transcript_list = MagicMock()
    mock_transcript_list.find_transcript.return_value = mock_transcript
    
    # Set up the mock API
    mock_transcript_api.list_transcripts.return_value = mock_transcript_list
    
    # Import actual exceptions to mock correctly
    from youtube_transcript_api import (
        TranscriptsDisabled,
        NoTranscriptFound
    )
    
    # Set up the exception classes on the mock
    mock_transcript_api.TranscriptsDisabled = TranscriptsDisabled
    mock_transcript_api.NoTranscriptFound = NoTranscriptFound
    
    # Configure the find_transcript method to return our mock transcript
    mock_transcript_list.find_transcript.side_effect = lambda langs: mock_transcript
    
    # Get the transcript
    transcript = youtube_handler.get_transcript('video_id')
    
    # Verify the result
    assert transcript == 'Hello World'
    
    # Verify the API was called correctly - update the patch path
    mock_transcript_api.list_transcripts.assert_called_once_with('video_id')
    mock_transcript_list.find_transcript.assert_called()
    mock_transcript.fetch.assert_called_once()

@patch('youtube_transcript_api.YouTubeTranscriptApi')
def test_get_transcript_no_transcript(mock_transcript_api, youtube_handler):
    # Mock transcript API to raise NoTranscriptFound
    mock_transcript_api.list_transcripts.side_effect = Exception('No transcript found')
    
    transcript = youtube_handler.get_transcript('video_id')
    assert transcript is None

def test_get_playlist_videos_invalid_url(youtube_handler):
    with pytest.raises(ValueError, match="Invalid YouTube playlist URL"):
        youtube_handler.get_playlist_videos("https://invalid.com/playlist")

@patch('yt_dlp.YoutubeDL')
def test_get_playlist_videos_empty_playlist(mock_ytdl, youtube_handler):
    # Mock empty playlist response
    mock_ytdl.return_value.__enter__.return_value.extract_info.return_value = {
        'title': 'Empty Playlist',
        'entries': []
    }
    
    with pytest.raises(ValueError) as exc_info:
        youtube_handler.get_playlist_videos('https://www.youtube.com/playlist?list=123')
    
    assert "No accessible videos found in the playlist" in str(exc_info.value) 