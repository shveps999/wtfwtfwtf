import os
import logfire
from .interfaces import FileStorageInterface
from .file_storage import LocalFileStorage
from .s3_storage import S3FileStorage

def has_s3_credentials() -> bool:
    """Проверить наличие данных для авторизации в S3"""
    required_vars = [
        "S3_BUCKET_NAME",
        "AWS_ACCESS_KEY_ID", 
        "AWS_SECRET_ACCESS_KEY"
    ]
    
    return all(os.getenv(var) for var in required_vars)

# Инициализируем файловое хранилище в зависимости от доступности S3
def get_file_storage() -> FileStorageInterface:
    """Получить подходящее файловое хранилище"""
    
    if has_s3_credentials():
        try:
            logfire.info("Initializing S3 storage with provided credentials")
            return S3FileStorage()
        except ValueError as e:
            logfire.warning(f"Failed to initialize S3 storage: {e}, falling back to local storage")
            return LocalFileStorage()
    else:
        logfire.info("No S3 credentials found, using local storage")
        return LocalFileStorage()

# Инициализируем файловое хранилище для использования во всем приложении
file_storage = get_file_storage()

__all__ = ["FileStorageInterface", "LocalFileStorage", "S3FileStorage", "file_storage", "get_file_storage"] 
