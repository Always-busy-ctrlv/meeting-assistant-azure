#!/bin/bash

echo "Deploying Python application..."

# Set environment variables
export SCM_DO_BUILD_DURING_DEPLOYMENT=true
export WEBSITE_RUN_FROM_PACKAGE=1
export PYTHONPATH=/home/site/wwwroot
export PYTHONUNBUFFERED=1
export LD_LIBRARY_PATH=/home/site/wwwroot/lib:$LD_LIBRARY_PATH

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y \
    libssl1.1 \
    libasound2 \
    libpulse0 \
    libpulse-dev \
    libasound2-dev \
    libffi-dev \
    portaudio19-dev \
    python3-pyaudio

# Create and configure PulseAudio
mkdir -p /tmp/pulse
chmod 777 /tmp/pulse
cat > /tmp/pulse/client.conf << EOF
default-server = unix:/tmp/pulse/native
autospawn = no
daemon-binary = /bin/true
enable-shm = false
EOF
chmod 644 /tmp/pulse/client.conf

# Create virtual environment if it doesn't exist
if [ ! -d "antenv" ]; then
    echo "Creating virtual environment..."
    python -m venv antenv
fi

# Activate virtual environment
source antenv/bin/activate

# Install Python packages
echo "Installing Python packages..."
pip install --upgrade pip
pip install setuptools wheel
pip install -r requirements.txt

# Start the application with Gunicorn
echo "Starting application..."
cd /home/site/wwwroot
gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 4 --threads 8 --worker-class gthread --log-level info wsgi:app 