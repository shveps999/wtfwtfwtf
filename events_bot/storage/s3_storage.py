import os
import uuid
from typing import Optional
from pathlib import Path
from aioboto3 import Session
from aiogram.types import InputMediaPhoto, URLInputFile
from botocore.exceptions import ClientError, NoCredentialsError
from .interfaces import FileStorageInterface
import logfire
from types_aiobotocore_s3 import Client


class S3FileStorage(FileStorageInterface):
    """S3 файловое хранилище для продакшена"""
    
    def __init__(
        self, 
        bucket_name: str = None,
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        region_name: str = None,
        endpoint_url: str = None
    ):
        """
            bucket_name: Имя S3 bucket
            aws_access_key_id: AWS Access Key ID
            aws_secret_access_key: AWS Secret Access Key
            region_name: AWS регион
            endpoint_url: URL эндпоинта (для совместимости с другими S3-совместимыми сервисами)
        """
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME")
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is required")
        
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables are required")
        
        logfire.info(f"S3 storage initialized with bucket: {self.bucket_name}, region: {self.region_name}")
        self.session: Session = Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name
        )
    
    async def save_file(self, file_data: bytes, file_extension: str) -> str:
        """Сохранить файл в S3"""
        # Генерируем уникальный id
        file_id = str(uuid.uuid4())
        key = f"{file_id}.{file_extension}"
        
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                use_ssl=False
            ) as s3_client:
                await s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_data,
                    ContentType=self._get_content_type(file_extension)
                )
                
            logfire.info(f"File saved to S3: {key}")
            return file_id
            
        except Exception as e:
            logfire.error(f"Error saving file to S3: {e}")
            raise
    
    async def get_media_photo(self, file_id: str) -> Optional[InputMediaPhoto]:
        """Получить файл как InputMediaPhoto для отправки в Telegram"""
        try:
            # Пробуем найти файл с разными расширениями
            for extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                key = f"{file_id}.{extension}"
                try:
                    # Генерируем временный URL для файла
                    url = await self.get_file_url(file_id, expires_in=3600)
                    if url:
                        logfire.info("File retrieved from S3: {key}, url: {url}", key=key, url=url)
                        return InputMediaPhoto(media=URLInputFile(url))
                except Exception:
                    continue
                            
            logfire.warning(f"File not found in S3: {file_id}")
            return None
            
        except Exception as e:
            logfire.error(f"Error retrieving file from S3: {e}")
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Удалить файл из S3 по id"""
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                use_ssl=False
            ) as s3_client:
                s3_client: Client
                # Пробуем удалить файл с разными расширениями
                for extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    key = f"{file_id}.{extension}"
                    try:
                        await s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                        logfire.info(f"File deleted from S3: {key}")
                        return True
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'NoSuchKey':
                            continue
                        else:
                            raise
                            
            logfire.warning(f"File not found for deletion in S3: {file_id}")
            return False
            
        except Exception as e:
            logfire.error(f"Error deleting file from S3: {e}")
            return False
    
    async def get_file_url(self, file_id: str, expires_in: int = 3600) -> Optional[str]:
        """Получить URL файла для прямого доступа (с временной ссылкой)"""
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                use_ssl=False
            ) as s3_client:
                s3_client: Client
                # Пробуем найти файл с разными расширениями
                for extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                    key = f"{file_id}.{extension}"
                    try:
                        # Проверяем существование файла
                        await s3_client.head_object(Bucket=self.bucket_name, Key=key)
                        
                        # Генерируем временный URL
                        url = await s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': self.bucket_name, 'Key': key},
                            ExpiresIn=expires_in
                        )
                        logfire.info("Generated presigned URL for: {key}, {url}", key=key, url=url)
                        return url
                    except ClientError as e:
                        if e.response['Error']['Code'] == 'NoSuchKey':
                            continue
                        else:
                            raise
                            
            logfire.warning(f"File not found for URL generation: {file_id}")
            return None
            
        except Exception as e:
            logfire.error(f"Error generating file URL: {e}")
            return None
    
    def _get_content_type(self, file_extension: str) -> str:
        """Определить Content-Type по расширению файла"""
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
        }
        return content_types.get(file_extension.lower(), 'application/octet-stream')
    
    async def test_connection(self) -> bool:
        """Тестировать подключение к S3"""
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url
            ) as s3_client:
                await s3_client.head_bucket(Bucket=self.bucket_name)
                logfire.info("S3 connection test successful")
                return True
        except Exception as e:
            logfire.error(f"S3 connection test failed: {e}")
            return False 
