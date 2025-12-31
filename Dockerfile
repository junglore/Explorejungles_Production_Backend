# Use official Python image
FROM python:3.11-slim

# Install ffmpeg (includes ffprobe)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy all project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (change if your app uses a different port)
EXPOSE 8000

# Default command: use the production startup script
CMD ["python", "start_with_large_limits.py"]
