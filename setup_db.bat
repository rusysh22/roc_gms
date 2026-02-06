@echo off
echo ==========================================
echo      GMS Database Setup Helper
echo ==========================================
echo.
echo This script will help you initialize a new database.
echo Make sure you have updated your .env file with the new credentials!
echo.
pause

echo.
echo [1/3] Applying Migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo Migration failed! Check your .env credentials.
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] Creating Superuser...
echo Please follow the prompts to create your admin account.
python manage.py createsuperuser

echo.
echo [3/3] Done!
echo You can now run the server with: python manage.py runserver
echo.
pause
