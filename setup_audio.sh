#!/bin/bash

# Create PulseAudio directories
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

# Verify PulseAudio is running
pactl info

echo "Audio setup complete" 