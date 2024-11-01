# Используем официальный образ Python
FROM python:3.12

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . .

# Устанавливаем зависимости проекта
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Playwright и системные зависимости для браузеров
RUN pip install playwright && \
    playwright install && \
    playwright install-deps

# Устанавливаем supervisord
RUN apt-get update && apt-get install -y supervisor

# Создаем директорию для логов
RUN mkdir -p /app/logs

# Открываем порт, на котором будет работать приложение
EXPOSE 8000

# Копируем файл конфигурации supervisord
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Команда запуска supervisord
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
