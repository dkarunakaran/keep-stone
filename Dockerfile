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
    cron \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /var/log/keepstone /var/run /app/static/uploads

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Setup crontab - every 3 hours
RUN echo "0 */3 * * * /usr/local/bin/python /app/scheduler.py >> /var/log/keepstone/scheduler.cron.log 2>&1" > /etc/cron.d/keepstone-cron
RUN chmod 0644 /etc/cron.d/keepstone-cron
RUN crontab /etc/cron.d/keepstone-cron

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

# Create startup script
RUN echo '#!/bin/bash\ncron\nexec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf' > /start.sh \
    && chmod +x /start.sh

# Start supervisor which will manage our processes
#CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

# Use the startup script as the entrypoint
CMD ["/start.sh"]