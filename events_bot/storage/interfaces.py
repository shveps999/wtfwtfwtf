from abc import ABC, abstractmethod
from typing import Optional
from aiogram.types import InputMediaPhoto


class FileStorageInterface(ABC):
    """Абстрактный интерфейс для файлового хранилища"""
    
    @abstractmethod
    async def save_file(self, file_data: bytes, file_extension: str) -> str:
        """
        Сохранить файл и вернуть его id
        
        Args:
            file_data: Данные файла в bytes
            file_extension: Расширение файла (например, 'jpg')
            
        Returns:
            str: Уникальный id файла
        """
        pass
    
    @abstractmethod
    async def get_media_photo(self, file_id: str) -> Optional[InputMediaPhoto]:
        """
        Получить файл как InputMediaPhoto для отправки в Telegram
        
        Args:
            file_id: Id файла
            
        Returns:
            Optional[InputMediaPhoto]: InputMediaPhoto или None если файл не найден
        """
        pass
    
    @abstractmethod
    async def get_file_url(self, file_id: str, expires_in: int = 3600) -> Optional[str]:
        """
        Получить URL файла для прямого доступа
        
        Args:
            file_id: Id файла
            expires_in: Время жизни URL в секундах (для S3)
            
        Returns:
            Optional[str]: URL файла или None если файл не найден
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """
        Удалить файл по id
        
        Args:
            file_id: Id файла
            
        Returns:
            bool: True если файл удален, False если файл не найден
        """
        pass 
