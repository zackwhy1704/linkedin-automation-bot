@echo off
echo ========================================
echo Installing ngrok
echo ========================================
echo.
echo Downloading ngrok for Windows...
echo.

:: Create a temp directory
if not exist "%TEMP%\ngrok" mkdir "%TEMP%\ngrok"

:: Download ngrok using PowerShell
powershell -Command "& {Invoke-WebRequest -Uri 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile '%TEMP%\ngrok\ngrok.zip'}"

echo.
echo Extracting ngrok...
powershell -Command "& {Expand-Archive -Path '%TEMP%\ngrok\ngrok.zip' -DestinationPath '%CD%' -Force}"

echo.
echo ========================================
echo ngrok installed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
echo 2. Run: ngrok config add-authtoken YOUR_TOKEN
echo 3. Run: ngrok http 8080
echo.
pause
