FROM python:3.10-slim

WORKDIR /app

# Set working directory
WORKDIR /app

# Copy the entire `Domasna_4` folder into the image
COPY ../../ /app/Domasna_4

# Set the Python path to include the copied `Domasna_4` folder
ENV PYTHONPATH="/app:/app/Domasna_4"

# Install dependencies
WORKDIR /app/Domasna_4/analysis/fundamental_analysis_service
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5002

CMD ["python", "fundamental_analysis_service.py"]
