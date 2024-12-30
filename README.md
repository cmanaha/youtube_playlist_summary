# YouTube Playlist Analyzer

[![Tests](https://github.com/cmanaha/youtube-playlist-analyzer/actions/workflows/python-tests.yml/badge.svg?branch=main)](https://github.com/cmanaha/youtube-playlist-analyzer/actions/workflows/python-tests.yml)

A powerful tool for analyzing YouTube playlists using AI to categorize and summarize video content. Perfect for quickly digesting large playlists and organizing videos by topic.

## Overview

This tool downloads YouTube playlist transcripts, uses LLMs to categorize and summarize videos, and generates a beautiful markdown report organized by categories. It supports concurrent processing, hardware acceleration, and flexible filtering options.

## Features
- 🤖 Advanced LLM Integration with Ollama
- 🚀 High Performance Processing
- 📊 Smart Video Categorization
- 📝 Intelligent Video Summarization
- 🎯 Flexible Category Filtering
- 📈 Progress Tracking & Statistics
- ⚙️ Extensive Configuration Options
- 🖥️ Hardware Acceleration Support

- AI-powered video categorization and summarization using LLaMA models
- Concurrent video processing with configurable batch sizes
- GPU acceleration support for faster processing
- Category filtering to focus on specific topics
- Beautiful markdown output with thumbnails and summaries
- Progress tracking with ETA estimation
- Environment variable configuration
- Detailed performance metrics in verbose mode

## Installation

```
git clone https://github.com/yourusername/youtube-playlist-analyzer
cd youtube-playlist-analyzer
pip install -r requirements.txt
```

Copy the .env.template to .env and configure your settings:

```
cp .env.template .env
```

## Usage

Basic usage with a playlist URL:

```
python src/main.py --url "https://youtube.com/playlist?list=..."
```

Advanced usage with filters and hardware acceleration:

```
python src/main.py --url "..." --categories "Security,AIML" --num-gpus 1 --batch-size 4
```

## Configuration

The tool can be configured through command line arguments or environment variables:

| Parameter | Environment Variable | Description | Default |
|-----------|---------------------|-------------|---------|
| --url | PLAYLIST_URL | YouTube playlist URL | Required |
| --videos | VIDEOS | Number of videos to process | All |
| --categories | CATEGORIES | Categories to filter by | All |
| --batch-size | BATCH_SIZE | Concurrent processing batch size | 1 |
| --num-gpus | NUM_GPUS | Number of GPUs to use | 0 |
| --num-cpus | NUM_CPUS | Number of CPU cores to use | 4 |
| --model | MODEL | Ollama model to use | llama3.2 |
| --threads | THREADS | Number of CPU threads for LLM | 4 |
| --output | OUTPUT | Output file path | Auto-generated |
| --verbose | VERBOSE | Show detailed progress | false |


## Output Format

The generated markdown report includes:
- Table of contents with category links
- Videos organized by category
- Thumbnails and direct links to videos
- AI-generated two-sentence summaries
- Video count per category


## Development

Run tests:

```
pytest tests/
```

Code structure:
- main.py: Entry point and orchestration
- transcript_processor.py: AI processing logic
- youtube_handler.py: YouTube API interaction
- markdown_generator.py: Report generation
- utils.py: Helper functions and system detection

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.



