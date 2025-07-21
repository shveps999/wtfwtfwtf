#!/usr/bin/env bash

# Создаем bucket для хранения файлов бота
echo "Creating S3 bucket: events-bot-uploads"
awslocal s3 mb s3://events-bot-uploads

# Настраиваем CORS для bucket
echo "Configuring CORS for bucket"
awslocal s3api put-bucket-cors \
  --bucket events-bot-uploads \
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

echo "S3 bucket setup completed successfully" 
