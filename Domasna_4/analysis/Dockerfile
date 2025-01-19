FROM python:3.10-slim

WORKDIR /app

COPY ./ /app/Domasna_4

# Set the PYTHONPATH to include `/app`, `/app/Domasna_4`, and `/app/Domasna_4/analysis`
ENV PYTHONPATH=/app:/app/Domasna_4:/app/Domasna_4/analysis

#RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py"]
