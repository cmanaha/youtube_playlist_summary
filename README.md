# YouTube Playlist Summarizer

A tool that uses AI to analyze and summarize YouTube playlists, creating well-organized markdown documents with categorized video summaries.

**Author:** Carlos Manzanedo Rueda ([@cmanaha](https://github.com/cmanaha))


## Overview

This application processes YouTube playlists by downloading video transcripts, categorizing content using AI, and generating concise summaries. It's particularly useful for:
- Conference playlists (like AWS re:Invent, KubeCon, Google Next)
- Educational series
- Technical tutorials
- Product launches and keynotes

## Installation

### Local Installation

1. Clone the repository and install dependencies:
<pre>
git clone https://github.com/cmanaha/youtube_playlist_summary.git
cd youtube_playlist_summary
pip install -r requirements.txt
</pre>

2. Create a .env file from the template:
<pre>
cp .env.template .env
</pre>

3. Configure your environment variables (see Configuration section below)

### EC2 Installation

For EC2 deployment, use our installation script:
<pre>
curl -sSL https://raw.githubusercontent.com/yourusername/youtube_playlist_summary/main/scripts/install_ec2.sh | sudo bash
</pre>

## Configuration

The application can be configured through environment variables or a .env file. Here's a comprehensive guide to the configuration options:

### Model Selection

The application supports both local and cloud-based AI models:

#### Local Models (via Ollama)
- `llama3.2` (default): Balanced performance and quality
- `mistral`: Fast and efficient

#### Cloud Models (via AWS Bedrock)
- `claude`: Claude 3.5 Sonnet - Highest quality summaries
- `claude-haiku`: Claude 3.5 Haiku - Fast with good quality
- `nova`: Amazon Nova Lite - Efficient and cost-effective

### Basic Usage

1. Simple playlist analysis with default settings:
<pre>
# In your .env file:
PLAYLIST_URL=https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID
MODEL=llama3.2

# Run the application:
python src/main.py
</pre>

2. Advanced configuration example:
<pre>
PLAYLIST_URL=https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID
MODEL=claude
BATCH_SIZE=2
CATEGORIES=Security,AI & ML
VERBOSE=true
NUM_CPUS=4
</pre>

### Working with AWS Bedrock

To use Bedrock models (claude, claude-haiku, nova), configure AWS credentials:

<pre>
AWS_DEFAULT_REGION=us-east-1
AWS_PROFILE=default
</pre>

### Advanced Features

#### Category Filtering

Filter videos by specific categories:
<pre>
CATEGORIES=Security,AI & ML,GitOps
</pre>



#### Two-Stage Processing

For environments with YouTube API restrictions, use the two-stage approach:

1. Extract transcripts locally:
<pre>
python src/main.py --extract-transcripts transcripts.zip
</pre>

2. Transfer and process on target machine:
<pre>
# Copy transcripts to target machine
scp -i your-key.pem transcripts.zip ec2-user@your-ec2-instance:/opt/youtube_playlist_summary/

# Process with your chosen model
python src/main.py --with-transcripts transcripts.zip --model claude
</pre>

#### Batch Processing

Control concurrent processing:
<pre>
BATCH_SIZE=2  # Process two videos simultaneously
NUM_CPUS=4    # Utilize 4 CPU cores
NUM_GPUS=1    # Use GPU acceleration (for Ollama models)
THREADS=4     # Configure LLM threading
</pre>

### Output Customization

By default, summaries are saved in the `output/` directory. Customize the output:
<pre>
OUTPUT=custom/path/summary.md
</pre>

The generated markdown includes:
- Table of contents with category links
- Videos grouped by category
- Thumbnails and direct links
- Concise two-sentence summaries

## Model Comparison Guide

Choose your model based on your needs:

**Local Processing (Ollama)**
- `llama3.2`: Best for general use, good balance of speed and quality
- `mistral`: Faster alternative, suitable for larger playlists

**Cloud Processing (Bedrock)**
- `claude`: Best for technical content and accurate summaries
- `claude-haiku`: Good for quick processing of large playlists
- `nova`: Balanced option for general content

## Troubleshooting

Common issues and solutions:

1. YouTube API restrictions:
   - Use the two-stage processing approach
   - Extract transcripts locally, then process on target machine

2. Model availability:
   - Ensure Ollama is installed for local models
   - Verify AWS credentials for Bedrock models



## Contributing

Contributions are welcome! Please check our contributing guidelines and feel free to submit pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 