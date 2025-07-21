# Используем официальный Python образ
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем uv для управления зависимостями
RUN pip install uv

# Копируем файлы зависимостей
COPY pyproject.toml ./

# Устанавливаем зависимости
RUN uv sync

# Копируем исходный код
COPY . .


# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

# Открываем порт (если понадобится для веб-хуков)
EXPOSE 8080

# Команда запуска
CMD ["uv", "run", "python", "main.py"] 