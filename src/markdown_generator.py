import json

class MarkdownGenerator:
    def __init__(self, playlist_title: str):
        self.playlist_title = playlist_title
        self.categories = {}
        
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
            'summary': summary
        })
        
    def generate_markdown(self) -> str:
        """Generate markdown content."""
        lines = [
            f"# YouTube Playlist Summary: {self.playlist_title}\n",
            "## Table of Contents\n"
        ]
        
        # Add category links to table of contents
        for category in sorted(self.categories.keys()):
            category_link = category.lower().replace(' ', '-')
            lines.append(f"- [{category}](#{category_link}) ({len(self.categories[category])} videos)")
        
        # Add each category and its videos
        for category in sorted(self.categories.keys()):
            lines.append(f"\n## {category} ({len(self.categories[category])} videos)")
            
            for video in self.categories[category]:
                lines.extend([
                    "\n<table style='border: none; border-collapse: collapse;'><tr style='border: none;'>",
                    f"<td width='30%' style='border: none;'><a href='{video['url']}'><img src='{video['thumbnail']}' width='200'></a></td>",
                    f"<td valign='top' style='border: none;'><h4><a href='{video['url']}'>{video['title']}</a></h4>",
                    f"{video['summary']}</td>",
                    "</tr></table>\n"
                ])
        
        return '\n'.join(lines) 