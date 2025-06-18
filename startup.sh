#!/bin/bash

echo "Deploying Python application..."

# Set environment variables
export SCM_DO_BUILD_DURING_DEPLOYMENT=true
export WEBSITE_RUN_FROM_PACKAGE=1

# Create and activate virtual environment if it doesn't exist
if [ ! -d "/home/site/wwwroot/antenv" ]; then
    echo "Creating virtual environment..."
    python -m venv /home/site/wwwroot/antenv
fi

# Activate virtual environment
source /home/site/wwwroot/antenv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r /home/site/wwwroot/requirements.txt

# Start the application
echo "Starting application..."
cd /home/site/wwwroot
gunicorn --bind=0.0.0.0:$PORT --worker-class eventlet --workers 1 --timeout 120 --keepalive 5 --access-logfile - --error-logfile - --log-level info app:app 