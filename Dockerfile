FROM python:3.11-slim

# Install Chrome + dependencies for Selenium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg2 curl unzip \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libnspr4 \
    libnss3 libxcomposite1 libxdamage1 libxrandr2 xdg-utils \
    libxss1 libappindicator3-1 \
    && wget -q -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/screenshots /app/cookies /app/logs

# Set Chrome to run headless
ENV HEADLESS=True
ENV CHROME_BIN=/usr/bin/google-chrome
ENV DISPLAY=:99

CMD ["python", "multiuser/telegram_bot_multiuser.py"]
