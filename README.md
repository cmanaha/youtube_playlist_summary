# YouTube Playlist Summary

A Python tool to generate summaries of YouTube playlists using AI. Supports both AWS Bedrock (Claude) and Ollama models for processing.

## Features

- Automatic transcript extraction from YouTube videos
- AI-powered video categorization and summarization
- Concurrent video processing for faster results
- Cost tracking for AWS Bedrock usage
- Configurable via environment variables or command line
- Support for multiple LLM providers (AWS Bedrock Claude and Ollama)
- Markdown output with video thumbnails and summaries

## Prerequisites

- Python 3.10+
- AWS credentials configured (if using Claude)
- Ollama installed (if using local models)
- YouTube Data API access

## Installation

<pre>
# Clone the repository
git clone https://github.com/cmanaha/youtube-playlist-summary.git
cd youtube-playlist-summary

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
</pre>

## Configuration

Create a `.env` file in the project root:

<pre>
PLAYLIST_URL=https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID
MODEL=claude        # Use 'claude' for AWS Bedrock or 'llama3.2' for Ollama
BATCH_SIZE=10      # Number of concurrent video processes
VIDEO_COUNT=10     # Limit number of videos to process
VERBOSE=true       # Enable detailed logging
</pre>

## Usage

Basic usage:

<pre>
python src/main.py
</pre>

Advanced usage with command line arguments:

<pre>
python src/main.py \
  --playlist-url "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID" \
  --model claude \
  --batch-size 10 \
  --videos 5 \
  --categories "ai & ml,security" \
  --verbose
</pre>


## Output

The tool generates a markdown file in the `output/` directory with:
- Playlist title and overview
- Table of contents by category
- Video summaries with thumbnails
- Links to original videos

Example output:

<pre>
# AWS re:Invent 2024 Playlist Summary

## Table of Contents
- [AI & ML](#ai--ml) (5 videos)
- [Security](#security) (3 videos)
- [Serverless](#serverless) (2 videos)

## AI & ML
[Video thumbnail and summary...]
</pre>

## Cost Tracking

When using AWS Bedrock (Claude), the tool tracks and displays:
- Cost per API call
- Token usage (input/output)
- Accumulated session cost

## Development

Run tests:
<pre>
pytest
</pre>

Format code:
<pre>
black src/ tests/
</pre>

## License

MIT License - see LICENSE file for details.

## Author

Carlos Manzanedo Rueda ([@cmanaha](https://github.com/cmanaha)) 
