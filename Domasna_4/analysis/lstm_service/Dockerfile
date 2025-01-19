FROM python:3.10-slim

WORKDIR /app

COPY . /app

COPY requirements.txt.txt /app/requirements.txt.txt
RUN pip install --no-cache-dir -r requirements.txt.txt

EXPOSE 5004

CMD ["python", "lstm_service.py"]
