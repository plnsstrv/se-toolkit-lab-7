FROM python:3.12-slim

WORKDIR /app

# Устанавливаем зависимости через pip (uv не нужен внутри контейнера)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
