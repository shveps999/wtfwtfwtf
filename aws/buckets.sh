#!/usr/bin/env bash

# set -e: Прерывает выполнение скрипта при любой ошибке
set -e

# --- ИСПРАВЛЕНИЕ: Используем переменную для имени бакета для удобства ---
BUCKET_NAME="events-bot-uploads"

echo "Проверка S3 бакета: $BUCKET_NAME"

# --- ИСПРАВЛЕНИЕ: Идемпотентное создание бакета ---
# Команда `head-bucket` проверяет существование бакета.
# `2>/dev/null` подавляет вывод ошибки "NotFound", если бакет не существует.
# Скрипт продолжается в блоке `else` только если бакет нужно создать.
if awslocal s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
  echo "Бакет '$BUCKET_NAME' уже существует. Создание пропущено."
else
  echo "Бакет '$BUCKET_NAME' не найден. Создание..."
  awslocal s3 mb "s3://$BUCKET_NAME"
  echo "Бакет '$BUCKET_NAME' успешно создан."
fi

# --- ИСПРАВЛЕНИЕ: CORS настраивается в любом случае для гарантии актуальности ---
# Эта операция идемпотентна: повторное применение тех же настроек не вызывает ошибки.
echo "Применение CORS конфигурации для бакета '$BUCKET_NAME'..."
awslocal s3api put-bucket-cors \
  --bucket "$BUCKET_NAME" \
  --cors-configuration '{
    "CORSRules": [
      {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["ETag"]
      }
    ]
  }'

echo "Настройка S3 бакета успешно завершена."