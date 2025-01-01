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
    assert "# Test Playlist" in content
    assert "<h2 id='table-of-contents'>Table of Contents</h2>" in content
    assert "<h2 id='security'>Security</h2>" in content 