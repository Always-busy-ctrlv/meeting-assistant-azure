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
echo "default-server = unix:/tmp/pulse/native" > /tmp/pulse/client.conf
echo "autospawn = yes" >> /tmp/pulse/client.conf
echo "daemon-binary = /usr/bin/pulseaudio" >> /tmp/pulse/client.conf
echo "enable-shm = yes" >> /tmp/pulse/client.conf
chmod 644 /tmp/pulse/client.conf

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install Python packages
echo "Installing Python packages..."
python -m pip install --upgrade pip
pip install setuptools wheel
pip install -r requirements.txt

# Start the application with Gunicorn
echo "Starting application..."
cd /home/site/wwwroot
gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 --worker-class gthread --threads 4 --log-level info --chdir /home/site/wwwroot wsgi:app 