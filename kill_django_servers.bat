@echo off
echo Killing all Python and Django processes...

REM Kill processes by PID
taskkill /PID 31784 /F 2>nul
taskkill /PID 31464 /F 2>nul

REM Kill all Python processes (more thorough)
taskkill /IM python.exe /F 2>nul

REM Kill processes using port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do taskkill /PID %%a /F 2>nul

echo All Django server processes have been terminated.
echo You can now restart your server with: python manage.py runserver
pause