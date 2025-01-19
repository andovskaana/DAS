FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy application code and dependencies
COPY ../ /app/Domasna_4

# Set the PYTHONPATH to include `/app`, `/app/Domasna_4`, and `/app/Domasna_4/analysis`
ENV PYTHONPATH="/app:/app/Domasna_4:/app/Domasna_4/analysis"

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the application port
EXPOSE 5001

# Command to run the service
CMD ["python", "technical_analysis_service.py"]
