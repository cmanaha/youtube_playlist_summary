## EC2 Installation

You can quickly set up this application on an Amazon EC2 instance using the provided installation script. Here's how:

### Prerequisites

1. An EC2 instance running Amazon Linux 2023
   - Recommended instance type: t3.xlarge or better
   - At least 20GB of storage for the model and application
   - Security group with SSH access (port 22)

### Quick Installation

You can install the application using one of these methods:

#### Method 1: Direct Installation (Recommended)

<pre>
curl -sSL https://raw.githubusercontent.com/cmanaha/youtube_playlist_summary/main/scripts/install_ec2.sh | sudo bash
</pre>

#### Method 2: Manual Installation

1. Connect to your EC2 instance:
<pre>
ssh -i your-key.pem ec2-user@your-ec2-instance
</pre>

2. Download and run the installation script:
<pre>
curl -O https://raw.githubusercontent.com/cmanaha/youtube_playlist_summary/main/scripts/install_ec2.sh
chmod +x install_ec2.sh
sudo ./install_ec2.sh
</pre>

### Post-Installation

After successful installation:

1. Navigate to the application directory:
<pre>
cd /opt/youtube_playlist_summary
</pre>

2. Activate the virtual environment:
<pre>
source venv/bin/activate
</pre>

3. Configure the application by editing the .env file:
<pre>
nano .env
</pre>

4. Run the application:
<pre>
python src/main.py
</pre>

### Two-Stage Processing (for YouTube API Restrictions)

Due to YouTube API restrictions on EC2 instances, it's recommended to use a two-stage process:

1. On your local machine, extract transcripts:
<pre>
python src/main.py --extract-transcripts transcripts.zip
</pre>

2. Copy the transcripts to your EC2 instance:
<pre>
scp -i your-key.pem transcripts.zip ec2-user@your-ec2-instance:/opt/youtube_playlist_summary/
</pre>

3. On EC2, process the transcripts:
<pre>
python src/main.py --with-transcripts transcripts.zip
</pre>

### Troubleshooting

- If the installation fails, check the error messages and ensure your instance has enough resources
- Make sure your EC2 instance has internet access
- The Llama model download might take several minutes depending on your internet connection
- If you see YouTube API restrictions, use the two-stage process described above

### Environment Configuration

The installation creates a minimal .env file with these settings:

<pre>
# Environment configuration
PLAYLIST_URL=
BATCH_SIZE=1
MODEL=llama3.2
</pre>

You can adjust these settings according to your needs. The PLAYLIST_URL must be set before running the application. 