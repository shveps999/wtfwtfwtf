from typing import Optional
import aiofiles
import os
import uuid
from pathlib import Path
from aiogram.types import InputMediaPhoto, FSInputFile
import logfire # --- ИСПРАВЛЕНИЕ: Добавляем logfire для логирования ошибок ---

from .interfaces import FileStorageInterface


class LocalFileStorage(FileStorageInterface):
    """Локальное файловое хранилище через aiofiles"""

    # --- ИСПРАВЛЕНИЕ: Белый список разрешенных расширений файлов ---
    # Это критически важная мера безопасности для предотвращения загрузки вредоносных файлов.
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    
    def __init__(self, storage_path: str = "uploads"):
        """
        Args:
            storage_path: Путь к папке для хранения файлов
        """
        self.storage_path = Path(os.getcwd()) / Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def save_file(self, file_data: bytes, file_extension: str) -> str:
        """Сохранить файл локально с проверкой расширения."""
        # --- ИСПРАВЛЕНИЕ: Проверка расширения файла ---
        # Приводим расширение к нижнему регистру для унификации.
        normalized_extension = file_extension.lower().lstrip('.')
        if normalized_extension not in self.ALLOWED_EXTENSIONS:
            logfire.warning(f"Попытка загрузить файл с недопустимым расширением: {normalized_extension}")
            raise ValueError(f"Неподдерживаемый тип файла. Разрешены: {', '.join(self.ALLOWED_EXTENSIONS)}")

        # Генерируем уникальный id
        file_id = str(uuid.uuid4())
        file_path = self.storage_path / f"{file_id}.{normalized_extension}"
        
        try:
            # Сохраняем файл асинхронно
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_data)
            logfire.info(f"Файл успешно сохранен локально: {file_path}")
            return file_id
        except Exception as e:
            logfire.error(f"Ошибка при сохранении файла {file_path}: {e}", exc_info=True)
            # В случае ошибки выбрасываем исключение, чтобы вызывающий код мог его обработать
            raise e
    
    async def get_media_photo(self, file_id: str) -> Optional[InputMediaPhoto]:
        """Получить файл как InputMediaPhoto для отправки в Telegram"""
        # Ищем файл по id (проверяем все возможные расширения из нашего списка)
        for extension in self.ALLOWED_EXTENSIONS:
            file_path = self.storage_path / f"{file_id}.{extension}"
            if file_path.exists():
                return InputMediaPhoto(media=FSInputFile(str(file_path)))
        
        logfire.warning(f"Файл с ID {file_id} не найден в локальном хранилище.")
        return None
    
    async def get_file_url(self, file_id: str, expires_in: int = 3600) -> Optional[str]:
        """Получить URL файла для прямого доступа (в данном случае, локальный путь)"""
        # Ищем файл по id (проверяем все возможные расширения)
        for extension in self.ALLOWED_EXTENSIONS:
            file_path = self.storage_path / f"{file_id}.{extension}"
            if file_path.exists():
                # Возвращаем абсолютный путь к файлу
                return str(file_path.absolute())
        
        logfire.warning(f"URL для файла с ID {file_id} не может быть сгенерирован (файл не найден).")
        return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Удалить файл по id"""
        # Ищем файл по id
        deleted = False
        for extension in self.ALLOWED_EXTENSIONS:
            file_path = self.storage_path / f"{file_id}.{extension}"
            if file_path.exists():
                try:
                    file_path.unlink()
                    logfire.info(f"Файл {file_path} успешно удален.")
                    deleted = True
                    # Не выходим из цикла, чтобы удалить возможные дубликаты с разными расширениями
                except OSError as e:
                    logfire.error(f"Ошибка при удалении файла {file_path}: {e}", exc_info=True)
        
        if not deleted:
            logfire.warning(f"Попытка удалить несуществующий файл с ID: {file_id}")
            
        return deleted