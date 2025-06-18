#!/bin/bash

echo "Deploying Python application..."

# Set environment variables
export SCM_DO_BUILD_DURING_DEPLOYMENT=true
export WEBSITE_RUN_FROM_PACKAGE=1
export PYTHONPATH=/home/site/wwwroot
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/usr/local/lib:$LD_LIBRARY_PATH

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
    pulseaudio \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libavfilter-dev \
    libavdevice-dev

# Create PulseAudio directories and set permissions
mkdir -p /tmp/pulse
chmod 777 /tmp/pulse

# Start PulseAudio in system mode
pulseaudio --system --disallow-exit --no-cpu-limit --exit-idle-time=-1 &

# Wait for PulseAudio to start
sleep 2

# Create a cookie file
pactl load-module module-native-protocol-unix socket=/tmp/pulse/native
pactl load-module module-simple-protocol-tcp

# Set permissions
chmod 777 /tmp/pulse/native
chmod 777 /tmp/pulse/cookie

# Create and activate virtual environment if it doesn't exist
if [ ! -d "/home/site/wwwroot/antenv" ]; then
    echo "Creating virtual environment..."
    python -m venv /home/site/wwwroot/antenv
fi

# Activate virtual environment
source /home/site/wwwroot/antenv/bin/activate

# Install Python packages
echo "Installing Python packages..."
pip install --upgrade pip
pip install setuptools wheel
pip install -r /home/site/wwwroot/requirements.txt

# Start the application
echo "Starting application..."
cd /home/site/wwwroot
gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120 wsgi:app 