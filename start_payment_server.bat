@echo off
REM Start the payment server for Stripe redirect pages
echo ============================================================
echo PAYMENT SERVER STARTER
echo ============================================================
echo.
echo This server serves the payment success/cancel pages
echo that automatically close the Telegram webview.
echo.
echo Starting Flask server on port 5000...
echo.
python payment_server.py
