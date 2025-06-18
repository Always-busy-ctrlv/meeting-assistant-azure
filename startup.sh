#!/bin/bash

echo "Deploying Python application..."

# Set environment variables
export SCM_DO_BUILD_DURING_DEPLOYMENT=true
export WEBSITE_RUN_FROM_PACKAGE=1
export PYTHONPATH=/home/site/wwwroot
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu

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
    python3-pyaudio \
    pulseaudio

# Set up audio environment
bash /home/site/wwwroot/setup_audio.sh

# Create and activate virtual environment if it doesn't exist
if [ ! -d "/home/site/wwwroot/antenv" ]; then
    echo "Creating virtual environment..."
    python -m venv /home/site/wwwroot/antenv
fi

# Activate virtual environment
source /home/site/wwwroot/antenv/bin/activate

# Install setuptools first
echo "Installing setuptools..."
pip install --upgrade pip setuptools wheel

# Install requirements
echo "Installing requirements..."
pip install -r /home/site/wwwroot/requirements.txt

# Start the application
echo "Starting application..."
cd /home/site/wwwroot
gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120 wsgi:app 