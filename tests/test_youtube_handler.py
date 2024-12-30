import pytest
from youtube_handler import YoutubeHandler
from unittest.mock import patch, MagicMock
import yt_dlp

def test_validate_youtube_playlist_url():
    handler = YoutubeHandler()
    
    # Valid URLs
    valid_urls = [
        "https://www.youtube.com/playlist?list=PLxxxxxxxx",
        "https://www.youtube.com/watch?v=xxxxx&list=PLxxxxxxxx",
        "https://youtu.be/xxxxx?list=PLxxxxxxxx"
    ]
    for url in valid_urls:
        assert handler._validate_youtube_playlist_url(url), f"Should accept {url}"
    
    # Invalid URLs
    invalid_urls = [
        "",
        "https://www.youtube.com/watch?v=xxxxx",
        "https://www.example.com",
        "not_a_url"
    ]
    for url in invalid_urls:
        assert not handler._validate_youtube_playlist_url(url), f"Should reject {url}"

@patch('yt_dlp.YoutubeDL')
def test_get_playlist_videos_private_playlist(mock_ydl_class):
    handler = YoutubeHandler()
    
    # Mock the validation to return True for our test URL
    with patch.object(handler, '_validate_youtube_playlist_url', return_value=True):
        # Mock yt_dlp to simulate a private playlist
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = yt_dlp.utils.DownloadError("This playlist is private")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        with pytest.raises(ValueError, match="Could not access the playlist"):
            handler.get_playlist_videos("https://www.youtube.com/playlist?list=PLxxxxxxxx")

@patch('yt_dlp.YoutubeDL')
def test_get_playlist_videos_empty_playlist(mock_ydl_class):
    handler = YoutubeHandler()
    
    # Mock the validation to return True for our test URL
    with patch.object(handler, '_validate_youtube_playlist_url', return_value=True):
        # Mock yt_dlp to simulate an empty playlist
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {'entries': []}
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        with pytest.raises(ValueError, match="No accessible videos found"):
            handler.get_playlist_videos("https://www.youtube.com/playlist?list=PLxxxxxxxx")

@patch('yt_dlp.YoutubeDL')
def test_get_playlist_videos_success(mock_ydl_class):
    handler = YoutubeHandler()
    
    # Mock successful playlist data
    mock_playlist_data = {
        'title': 'Test Playlist',
        'entries': [
            {
                'id': 'video1',
                'title': 'Test Video 1',
                'description': 'Description 1'
            },
            {
                'id': 'video2',
                'title': 'Test Video 2',
                'description': 'Description 2'
            }
        ]
    }
    
    # Mock the validation to return True for our test URL
    with patch.object(handler, '_validate_youtube_playlist_url', return_value=True):
        # Setup mock yt_dlp
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = mock_playlist_data
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
        
        videos, title = handler.get_playlist_videos("https://www.youtube.com/playlist?list=PLxxxxxxxx")
        
        assert title == 'Test Playlist'
        assert len(videos) == 2
        assert videos[0]['video_id'] == 'video1'
        assert videos[1]['title'] == 'Test Video 2'

def test_get_transcript(sample_video):
    handler = YoutubeHandler()
    with patch('youtube_transcript_api.YouTubeTranscriptApi.get_transcript') as mock_get_transcript:
        mock_get_transcript.return_value = [
            {'text': 'First part'},
            {'text': 'Second part'}
        ]
        transcript = handler.get_transcript(sample_video['video_id'])
        assert transcript == 'First part Second part' 