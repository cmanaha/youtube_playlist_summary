import pytest
from unittest.mock import patch, MagicMock
from youtube_handler import YoutubeHandler

def test_init(youtube_handler):
    assert youtube_handler.videos == []

@pytest.mark.parametrize('video_id,expected_title', [
    ('123456', 'Test Video'),
    ('abcdef', 'Another Test Video'),
])
@patch('yt_dlp.YoutubeDL')
def test_get_playlist_videos(mock_ydl, youtube_handler, video_id, expected_title):
    # Setup mock
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.extract_info.return_value = {
        'title': 'Test Playlist',
        'entries': [{
            'id': video_id,
            'title': expected_title,
            'description': 'Test description'
        }]
    }
    mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
    
    # Test
    videos, playlist_title = youtube_handler.get_playlist_videos('playlist_url')
    
    assert len(videos) == 1
    assert videos[0]['video_id'] == video_id
    assert videos[0]['title'] == expected_title
    assert videos[0]['url'] == f'https://www.youtube.com/watch?v={video_id}'
    assert playlist_title == 'Test Playlist'

@patch('youtube_handler.YouTubeTranscriptApi')
def test_get_transcript(mock_transcript_api, youtube_handler):
    # Setup mock
    mock_transcript_api.get_transcript.return_value = [
        {'text': 'First part'},
        {'text': 'Second part'}
    ]
    
    # Test
    transcript = youtube_handler.get_transcript('123456')
    
    assert transcript == 'First part Second part'
    mock_transcript_api.get_transcript.assert_called_once_with('123456') 