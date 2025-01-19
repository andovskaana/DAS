FROM python:3.10-slim

WORKDIR /app

COPY . /app

COPY requirements.txt.txt /app/requirements.txt.txt
RUN pip install --no-cache-dir -r requirements.txt.txt

EXPOSE 5001

CMD ["python", "technical_analysis_service.py"]
