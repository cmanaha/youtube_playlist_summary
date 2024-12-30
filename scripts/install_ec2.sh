#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    error "Please run as root (use sudo)"
fi

# Update system
log "Updating system packages..."
dnf update -y || error "Failed to update system packages"

# Install development tools and libraries
log "Installing development tools and libraries..."
dnf groupinstall "Development Tools" -y || error "Failed to install development tools"
dnf install -y \
    wget \
    git \
    python3 \
    python3-pip \
    python3-devel \
    openssl-devel \
    bzip2-devel \
    libffi-devel \
    || error "Failed to install required packages"

# Install Ollama
log "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh || error "Failed to install Ollama"

# Start Ollama service
log "Starting Ollama service..."
systemctl start ollama || error "Failed to start Ollama service"
systemctl enable ollama || error "Failed to enable Ollama service"

# Wait for Ollama service to be ready
log "Waiting for Ollama service to be ready..."
sleep 5

# Pull Llama model
log "Pulling Llama 3.2 model (this may take a while)..."
ollama pull llama3.2 || error "Failed to pull Llama model"

# Create application directory
APP_DIR="/opt/youtube_playlist_summary"
log "Creating application directory at ${APP_DIR}..."
mkdir -p ${APP_DIR}

# Clone repository
log "Cloning repository..."
git clone https://github.com/cmanaha/youtube_playlist_summary.git ${APP_DIR} || error "Failed to clone repository"

# Setup Python virtual environment
log "Setting up Python virtual environment..."
cd ${APP_DIR}
python3 -m venv venv || error "Failed to create virtual environment"
source venv/bin/activate || error "Failed to activate virtual environment"

# Install Python dependencies
log "Installing Python dependencies..."
pip install --upgrade pip || error "Failed to upgrade pip"
pip install -r requirements.txt || error "Failed to install Python dependencies"

# Create .env file template
log "Creating .env file template..."
cat > ${APP_DIR}/.env << EOL
# Environment configuration
PLAYLIST_URL=
BATCH_SIZE=1
MODEL=llama3.2
EOL

# Set permissions
log "Setting permissions..."
chown -R ec2-user:ec2-user ${APP_DIR}

# Print success message
log "Installation completed successfully!"
echo -e "${GREEN}To use the application:${NC}"
echo -e "1. Switch to application directory: ${YELLOW}cd ${APP_DIR}${NC}"
echo -e "2. Activate virtual environment: ${YELLOW}source venv/bin/activate${NC}"
echo -e "3. Edit .env file with your settings: ${YELLOW}nano .env${NC}"
echo -e "4. Run the application: ${YELLOW}python src/main.py${NC}" 