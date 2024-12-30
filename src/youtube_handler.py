import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
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
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.videos = []
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True
        }
        
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from URL."""
        pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
        match = re.search(pattern, url)
        return match.group(1) if match else None
        
    def get_playlist_videos(self, playlist_url: str) -> tuple[list, str]:
        """Get list of videos from a playlist."""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': True
        }
        
        # Use context manager to suppress output if not verbose
        with suppress_stdout_stderr() if not self.verbose else nullcontext():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(playlist_url, download=False)
        
        playlist_title = result.get('title', 'playlist')
        videos = []
        
        for entry in result['entries']:
            try:
                video_info = self._get_video_info(entry)
                if video_info:
                    videos.append(video_info)
            except Exception as e:
                print(f"Warning: Could not process video {entry.get('title', 'Unknown')}: {str(e)}")
                continue
        
        self.videos = videos
        return videos, playlist_title
    
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
    
    @retry_on_exception(retries=3, delay=2)
    def get_transcript(self, video_id) -> Optional[str]:
        """Get transcript for a video."""
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return ' '.join([entry['text'] for entry in transcript])
        except Exception as e:
            print(f"Warning: Could not get transcript for video {video_id}: {str(e)}")
            return None 