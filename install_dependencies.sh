#!/bin/bash

# Install required system libraries for Azure Speech SDK
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