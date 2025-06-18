@echo off
echo Deploying Python application...

:: Create and activate virtual environment
python -m venv env
call env\Scripts\activate

:: Install requirements
pip install -r requirements.txt

:: Set environment variables
set SCM_DO_BUILD_DURING_DEPLOYMENT=true
set WEBSITE_RUN_FROM_PACKAGE=1

:: Start the application
echo Starting application...
gunicorn --bind=0.0.0.0:%HTTP_PLATFORM_PORT% --worker-class eventlet --workers 1 --timeout 120 --keepalive 5 --access-logfile - --error-logfile - --log-level info app:app 