#!/usr/bin/env bash

# Проверяем список bucket
echo "Checking S3 buckets:"
awslocal s3 ls

# Проверяем содержимое bucket events-bot-uploads
echo -e "\nChecking contents of events-bot-uploads bucket:"
awslocal s3 ls s3://events-bot-uploads || echo "Bucket events-bot-uploads not found"

# Проверяем CORS настройки
echo -e "\nChecking CORS configuration:"
awslocal s3api get-bucket-cors --bucket events-bot-uploads || echo "CORS not configured" 
