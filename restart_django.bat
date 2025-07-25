@echo off
echo Restarting Django Development Environment...
echo.

echo Step 1: Killing all Python processes...
taskkill /IM python.exe /F 2>nul
timeout /t 2 >nul

echo.
echo Step 2: Starting Vite dev server...
start cmd /k "cd /d D:\Dev\dcdg\dcdg && npm run dev"
timeout /t 3 >nul

echo.
echo Step 3: Starting Django server...
cd /d D:\Dev\dcdg\dcdg
python manage.py runserver

pause