import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import time
from typing import List, Dict, Optional
from functools import wraps
import logging
import re
import sys
import os
from contextlib import contextmanager
import io
from contextlib import nullcontext
import requests
from utils import TranscriptData

def retry_on_exception(retries=3, delay=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:  # Last attempt
                        raise e
                    logging.warning(f"Attempt {attempt + 1} failed, retrying in {delay} seconds...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@contextmanager
def suppress_stdout_stderr():
    """Context manager to suppress stdout and stderr."""
    # Save the original stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    # Create a null device to redirect output
    null_device = open(os.devnull, 'w')
    
    try:
        # Redirect stdout/stderr to the null device
        sys.stdout = null_device
        sys.stderr = null_device
        yield
    finally:
        # Restore original stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        null_device.close()

class YoutubeHandler:
    def __init__(self, verbose: bool = False, saved_transcripts: Optional[Dict[str, TranscriptData]] = None):
        self.verbose = verbose
        self.videos = []
        self.saved_transcripts = saved_transcripts or {}
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True
        }
    
    def _validate_youtube_playlist_url(self, url: str) -> bool:
        """Validate if the URL is a YouTube playlist URL."""
        youtube_patterns = [
            r'youtube\.com/playlist\?list=[A-Za-z0-9_-]+$',  # Standard playlist URL
            r'youtube\.com/watch\?v=[A-Za-z0-9_-]+&list=[A-Za-z0-9_-]+',  # Video in playlist URL
            r'youtu\.be/[A-Za-z0-9_-]+\?list=[A-Za-z0-9_-]+'  # Shortened URL with playlist
        ]
        return any(re.search(pattern, url) is not None for pattern in youtube_patterns)
    
    def get_playlist_videos(self, playlist_url: str) -> tuple[list, str]:
        """Get list of videos from a playlist."""
        # Validate URL first
        if not playlist_url:
            raise ValueError("No playlist URL provided. Please provide a valid YouTube playlist URL.")
            
        if not self._validate_youtube_playlist_url(playlist_url):
            raise ValueError(
                "Invalid YouTube playlist URL. Please provide a URL in one of these formats:\n"
                "- https://www.youtube.com/playlist?list=PLAYLIST_ID\n"
                "- https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID\n"
                "- https://youtu.be/VIDEO_ID?list=PLAYLIST_ID"
            )
        
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                result = ydl.extract_info(playlist_url, download=False)
                
            if not result or 'entries' not in result:
                raise ValueError(
                    "Could not find any videos in the playlist. "
                    "Please check if the playlist exists and is not private."
                )
                
            playlist_title = result.get('title', 'playlist')
            videos = []
            
            for entry in result['entries']:
                try:
                    video_info = self._get_video_info(entry)
                    if video_info:
                        videos.append(video_info)
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Could not process video {entry.get('title', 'Unknown')}: {str(e)}")
                    continue
            
            if not videos:
                raise ValueError(
                    "No accessible videos found in the playlist. "
                    "The playlist might be empty or all videos might be private/unavailable."
                )
            
            self.videos = videos
            return videos, playlist_title
            
        except yt_dlp.utils.DownloadError as e:
            raise ValueError(
                f"Could not access the playlist. Please check that:\n"
                f"1. The URL is correct\n"
                f"2. The playlist is not private\n"
                f"3. The playlist still exists\n"
                f"Original error: {str(e)}"
            ) from None
        except Exception as e:
            raise ValueError(
                f"An error occurred while processing the playlist: {str(e)}"
            ) from None
    
    @retry_on_exception(retries=3, delay=2)
    def _get_video_info(self, entry: Dict) -> Optional[Dict]:
        """Get video information with retries."""
        url = f"https://www.youtube.com/watch?v={entry['id']}"
        return {
            'title': entry['title'],
            'url': url,
            'video_id': entry['id'],
            'description': entry.get('description', '')
        }
    
    @retry_on_exception(retries=3, delay=5)
    def get_transcript(self, video_id) -> Optional[str]:
        """Get transcript for a video, either from saved data or YouTube."""
        # Check if we have this transcript saved
        if video_id in self.saved_transcripts:
            if self.verbose:
                print(f"Using saved transcript for video {video_id}")
            return self.saved_transcripts[video_id].transcript
            
        # If not saved, proceed with YouTube API call
        try:
            # First try to get available transcript languages
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get English transcript first
            try:
                transcript = transcript_list.find_transcript(['en'])
            except NoTranscriptFound:
                # If no English transcript, try to get any transcript and translate it
                try:
                    transcript = transcript_list.find_transcript(['en-US', 'en-GB'])
                except NoTranscriptFound:
                    # Get any available transcript and translate to English
                    transcript = transcript_list.find_manually_created_transcript()
                    transcript = transcript.translate('en')

            # Get the actual transcript data
            transcript_data = transcript.fetch()
            return ' '.join([entry['text'] for entry in transcript_data])

        except TranscriptsDisabled:
            if self.verbose:
                print(f"Warning: Transcripts are disabled for video {video_id}")
            return None
        except NoTranscriptFound:
            if self.verbose:
                print(f"Warning: No transcript found for video {video_id}")
            return None
        except Exception as e:
            if self.verbose:
                print(f"Warning: Could not get transcript for video {video_id}: {str(e)}")
            return None

    def _check_video_availability(self, video_id: str) -> bool:
        """Check if a video is available and not region-restricted."""
        try:
            # Try to access video metadata using yt-dlp
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", 
                               download=False,
                               process=False)
            return True
        except Exception as e:
            if self.verbose:
                print(f"Warning: Video {video_id} is not accessible: {str(e)}")
            return False 