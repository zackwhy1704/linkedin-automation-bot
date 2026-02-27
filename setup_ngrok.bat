@echo off
echo ========================================
echo ngrok Authentication Setup
echo ========================================
echo.
echo Please enter your ngrok authtoken from:
echo https://dashboard.ngrok.com/get-started/your-authtoken
echo.
set /p AUTHTOKEN="Enter authtoken: "
echo.
echo Configuring ngrok...
ngrok config add-authtoken %AUTHTOKEN%
echo.
echo ========================================
echo ngrok configured successfully!
echo ========================================
echo.
echo Now run: ngrok http 8080
echo.
pause
