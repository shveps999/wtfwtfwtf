import os
import uuid
from typing import Optional
from pathlib import Path
from aioboto3 import Session
from aiogram.types import InputMediaPhoto, URLInputFile
from botocore.exceptions import ClientError, NoCredentialsError
import logfire
from types_aiobotocore_s3 import Client

from .interfaces import FileStorageInterface


class S3FileStorage(FileStorageInterface):
    """S3 файловое хранилище для продакшена"""
    
    # --- ИСПРАВЛЕНИЕ: Белый список разрешенных расширений, как и в LocalFileStorage ---
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    
    def __init__(
        self, 
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str,
        endpoint_url: Optional[str]
    ):
        """
        Приватный конструктор. Используйте асинхронный метод `create` для создания экземпляра.
        """
        self.bucket_name = bucket_name
        self.session = Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        self.endpoint_url = endpoint_url
        logfire.info(f"Экземпляр S3 storage создан для бакета: {self.bucket_name}")

    @classmethod
    async def create(cls, 
        bucket_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
        endpoint_url: Optional[str] = None
    ):
        """
        Асинхронный фабричный метод для создания и проверки экземпляра S3FileStorage.
        Гарантирует, что соединение с S3 успешно установлено перед использованием.
        """
        b_name = bucket_name or os.getenv("S3_BUCKET_NAME")
        ak_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        sak = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        r_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        ep_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")

        if not b_name:
            raise ValueError("S3_BUCKET_NAME не указан в переменных окружения.")
        if not ak_id or not sak:
            raise ValueError("AWS_ACCESS_KEY_ID и AWS_SECRET_ACCESS_KEY должны быть указаны.")
        
        instance = cls(b_name, ak_id, sak, r_name, ep_url)
        
        await instance.test_connection()
        
        logfire.info(f"S3 хранилище успешно инициализировано для бакета: {instance.bucket_name}")
        return instance

    async def test_connection(self):
        """
        Тестирует соединение с S3, проверяя доступность бакета.
        Выбрасывает исключение в случае ошибки.
        """
        logfire.info(f"Проверка соединения с S3 и доступности бакета '{self.bucket_name}'...")
        try:
            async with self.session.client('s3', endpoint_url=self.endpoint_url) as s3_client:
                await s3_client.head_bucket(Bucket=self.bucket_name)
            logfire.info("✅ Соединение с S3 успешно установлено.")
        except (NoCredentialsError, ClientError) as e:
            logfire.error(f"❌ ОШИБКА: Не удалось подключиться к S3. Проверьте учетные данные и имя бакета. Детали: {e}", exc_info=True)
            raise ConnectionError(f"Не удалось подключиться к S3: {e}")
        except Exception as e:
            logfire.error(f"❌ ОШИБКА: Непредвиденная ошибка при подключении к S3: {e}", exc_info=True)
            raise ConnectionError(f"Непредвиденная ошибка S3: {e}")

    async def save_file(self, file_data: bytes, file_extension: str) -> str:
        """Сохранить файл в S3 с проверкой расширения."""
        normalized_extension = file_extension.lower().lstrip('.')
        if normalized_extension not in self.ALLOWED_EXTENSIONS:
            logfire.warning(f"Попытка загрузить файл с недопустимым расширением в S3: {normalized_extension}")
            raise ValueError(f"Неподдерживаемый тип файла. Разрешены: {', '.join(self.ALLOWED_EXTENSIONS)}")

        file_id = str(uuid.uuid4())
        key = f"{file_id}.{normalized_extension}"
        
        try:
            async with self.session.client('s3', endpoint_url=self.endpoint_url) as s3_client:
                await s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=file_data,
                    ContentType=self._get_content_type(normalized_extension)
                )
            logfire.info(f"Файл сохранен в S3: {key}")
            return file_id
        except Exception as e:
            logfire.error(f"Ошибка при сохранении файла в S3: {e}", exc_info=True)
            raise

    async def get_media_photo(self, file_id: str) -> Optional[InputMediaPhoto]:
        """Получить файл как InputMediaPhoto для отправки в Telegram, используя временный URL."""
        try:
            url = await self.get_file_url(file_id, expires_in=60) # Генерируем URL на короткий срок
            if url:
                logfire.info(f"Получен временный URL для файла {file_id} для отправки в Telegram.")
                # URLInputFile используется для отправки файла по URL
                return InputMediaPhoto(media=URLInputFile(url))
            
            logfire.warning(f"Не удалось получить URL для файла {file_id}, файл не найден в S3.")
            return None
        except Exception as e:
            logfire.error(f"Ошибка при получении media photo из S3 для файла {file_id}: {e}", exc_info=True)
            return None

    async def delete_file(self, file_id: str) -> bool:
        """Удалить файл из S3 по id."""
        deleted = False
        try:
            async with self.session.client('s3', endpoint_url=self.endpoint_url) as s3_client:
                s3_client: Client
                for extension in self.ALLOWED_EXTENSIONS:
                    key = f"{file_id}.{extension}"
                    try:
                        # Сначала проверяем, существует ли объект, чтобы избежать лишних ошибок
                        await s3_client.head_object(Bucket=self.bucket_name, Key=key)
                        # Если существует, удаляем
                        await s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                        logfire.info(f"Файл удален из S3: {key}")
                        deleted = True
                        # Можно выйти из цикла после первого же успешного удаления
                        break 
                    except ClientError as e:
                        # Если ключ не найден, это не ошибка, просто продолжаем поиск
                        if e.response['Error']['Code'] in ('404', 'NoSuchKey'):
                            continue
                        else:
                            # Другие ошибки ClientError (например, нет прав) нужно логировать и пробрасывать
                            logfire.error(f"ClientError при удалении файла {key} из S3: {e}", exc_info=True)
                            raise
            if not deleted:
                 logfire.warning(f"Файл с ID {file_id} не найден для удаления в S3.")
            return deleted
        except Exception as e:
            logfire.error(f"Критическая ошибка при удалении файла {file_id} из S3: {e}", exc_info=True)
            return False

    async def get_file_url(self, file_id: str, expires_in: int = 3600) -> Optional[str]:
        """Получить URL файла для прямого доступа (с временной ссылкой)"""
        try:
            async with self.session.client('s3', endpoint_url=self.endpoint_url) as s3_client:
                s3_client: Client
                for extension in self.ALLOWED_EXTENSIONS:
                    key = f"{file_id}.{extension}"
                    try:
                        await s3_client.head_object(Bucket=self.bucket_name, Key=key)
                        url = await s3_client.generate_presigned_url(
                            'get_object', Params={'Bucket': self.bucket_name, 'Key': key}, ExpiresIn=expires_in
                        )
                        return url
                    except ClientError as e:
                        if e.response['Error']['Code'] in ('404', 'NoSuchKey'):
                            continue
                        else:
                            raise
            return None
        except Exception as e:
            logfire.error(f"Ошибка при генерации URL для файла: {e}", exc_info=True)
            return None

    def _get_content_type(self, file_extension: str) -> str:
        """Определить Content-Type по расширению файла"""
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
        }
        return content_types.get(file_extension.lower(), 'application/octet-stream')