FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Установка языковой модели spaCy
RUN python -m spacy download uk_core_news_sm

# Переменная окружения для порта
ENV PORT=10000

# Запуск приложения
CMD gunicorn --bind 0.0.0.0:$PORT main:app
