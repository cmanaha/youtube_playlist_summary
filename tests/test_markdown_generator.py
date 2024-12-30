import pytest
from markdown_generator import MarkdownGenerator

def test_markdown_generator_initialization():
    generator = MarkdownGenerator("Test Playlist")
    assert generator.playlist_title == "Test Playlist"

def test_markdown_generation():
    generator = MarkdownGenerator("Test Playlist")
    generator.add_video("Security", 
                       {"title": "Test Video", "url": "http://test.com"},
                       "Test summary")
    
    content = generator.generate_markdown()
    assert "# YouTube Playlist Summary: Test Playlist" in content
    assert "## Table of Contents" in content
    assert "## Security (1 videos)" in content 