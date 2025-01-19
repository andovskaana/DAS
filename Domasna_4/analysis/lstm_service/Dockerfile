FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy the entire `Domasna_4` folder to `/app/Domasna_4` inside the container
COPY Domasna_4 /app/Domasna_4

# Set the Python path to include the `Domasna_4` directory for imports
ENV PYTHONPATH="/app/Domasna_4"

# Navigate to the specific service directory to install dependencies
WORKDIR /app/Domasna_4/analysis/lstm_service

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5004

CMD ["python", "lstm_service.py"]
