# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# Install system dependencies
RUN apt-get update && apt-get install -y \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /var/log/keepstone /var/run /app/instance/static/uploads

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy application code
#COPY . .

RUN mkdir -p static/uploads
RUN mkdir logs

# Set permissions
RUN chown -R www-data:www-data /app/static/uploads \
    && chown -R www-data:www-data /var/log/keepstone

# Expose port
EXPOSE 2222

# Start supervisor which will manage our processes
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]