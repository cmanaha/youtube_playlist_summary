"""
YouTube Playlist Summary
Copyright (c) 2024 Carlos Manzanedo Rueda (@cmanaha)

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://opensource.org/licenses/MIT
"""

import json
from typing import Dict, List, Any
from collections import defaultdict

class MarkdownGenerator:
    def __init__(self, playlist_title: str):
        self.playlist_title = playlist_title
        self.content = []
        self.toc_anchor = "table-of-contents"
        self.categories: Dict[str, List[Dict[str, Any]]] = {}
    
    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        if 'v=' in url:
            return url.split('v=')[1].split('&')[0]
        return ''
    
    def add_video(self, category: str, video_info: dict, summary: str):
        """Add a video to a category."""
        if category not in self.categories:
            self.categories[category] = []
        
        video_id = self._extract_video_id(video_info['url'])
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/0.jpg"
        
        self.categories[category].append({
            'title': video_info['title'],
            'url': video_info['url'],
            'thumbnail': thumbnail_url,
            'summary': summary,
            'speaker': video_info.get('speaker', 'N/A')
        })
    
    def _format_video_entry(self, video: Dict[str, Any]) -> str:
        """Format a single video entry with thumbnail and summary."""
        return f"""
<table style='border: none; border-collapse: collapse; width: 100%;'><tr style='border: none;'>
<td width='30%' style='border: none;'><a href='{video['url']}'><img src='{video['thumbnail']}' width='200'></a></td>
<td valign='top' style='border: none;'>
<h3><a href='{video['url']}'>{video['title']}</a></h3>
{video['summary']}
<div style='text-align: right; font-size: 0.8em;'><a href='#{self.toc_anchor}'>back to top</a></div>
</td>
</tr></table>"""

    def generate_markdown(self) -> str:
        """Generate markdown content with table of contents and categorized videos."""
        # Start with title and TOC
        self.content = [
            f"# {self.playlist_title}\n",
            f"<h2 id='{self.toc_anchor}'>Table of Contents</h2>\n"
        ]
        
        # Add categories to TOC
        for category in sorted(self.categories.keys()):
            if self.categories[category]:  # Only add categories with videos
                safe_category = category.replace(" ", "-").lower()
                self.content.append(f"- [{category}](#{safe_category}) ({len(self.categories[category])} videos)")
        
        self.content.append("\n")  # Add spacing after TOC
        
        # Add categorized content
        for category in sorted(self.categories.keys()):
            if self.categories[category]:  # Only add categories with videos
                safe_category = category.replace(" ", "-").lower()
                # Use HTML for category headers with hidden anchors
                self.content.append(f"\n<h2 id='{safe_category}'>{category}</h2>\n")
                
                # Add each video in the category
                for video in self.categories[category]:
                    self.content.append(self._format_video_entry(video))
        
        return "\n".join(self.content) 