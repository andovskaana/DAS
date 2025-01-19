FROM python:3.10-slim

WORKDIR /app

COPY . /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5002

CMD ["python", "fundamental_analysis_service.py"]
