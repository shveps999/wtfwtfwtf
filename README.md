# Events Bot

Современная асинхронная архитектура Telegram бота, построенная на SQLAlchemy 2.0 и aiogram 3.0.

## Архитектурные особенности

- **Асинхронная архитектура**: Полностью неблокирующие операции
- **Масштабируемость**: Поддержка множественных подключений к БД
- **Гибкость БД**: Поддержка PostgreSQL, MySQL и SQLite
- **Современный стек**: SQLAlchemy 2.0 с async/await
- **Инлайн-интерфейс**: Все взаимодействие через inline-кнопки
- **Модульная структура**: Разделение на слои (handlers, services, repositories)

## Структура Базы Данных

### Основные таблицы:

1. **users** - Пользователи Telegram
   - `id` - ID пользователя в Telegram (первичный ключ)
   - `username` - Имя пользователя
   - `first_name`, `last_name` - Имя и фамилия
   - `created_at` - Дата регистрации (автоматически)
   - `updated_at` - Дата обновления (автоматически)
   - `is_active` - Активность пользователя

2. **categories** - Категории постов
   - `id` - Первичный ключ
   - `name` - Название категории
   - `description` - Описание категории
   - `created_at` - Дата создания (автоматически)
   - `updated_at` - Дата обновления (автоматически)
   - `is_active` - Активность категории

3. **posts** - Посты пользователей
   - `id` - Первичный ключ
   - `title` - Заголовок поста
   - `content` - Содержание поста
   - `author_id` - ID автора (связь с users)
   - `category_id` - ID категории (связь с categories)
   - `created_at` - Дата создания (автоматически)
   - `updated_at` - Дата обновления (автоматически)
   - `is_approved` - Статус одобрения
   - `is_published` - Статус публикации
   - `published_at` - Дата публикации

4. **moderation_records** - Записи модерации
   - `id` - Первичный ключ
   - `post_id` - ID поста
   - `moderator_id` - ID модератора
   - `action` - Действие (enum: APPROVE=1, REJECT=2, REQUEST_CHANGES=3)
   - `comment` - Комментарий модератора
   - `created_at` - Дата действия (автоматически)
   - `updated_at` - Дата обновления (автоматически)

5. **user_categories** - Связь многие-ко-многим между пользователями и категориями

## Производительность

### ⚡ Асинхронная архитектура
- **Многопоточность**: Обработка множественных запросов одновременно
- **Неблокирующие операции**: I/O операции не блокируют основной поток
- **Эффективное использование ресурсов**: Минимальное потребление CPU и памяти

### 🗄️ Оптимизация базы данных
- **Connection Pooling**: Переиспользование соединений с БД
- **Lazy Loading**: Загрузка связанных данных по требованию
- **Индексы**: Оптимизированные запросы для быстрого поиска
- **Batch Operations**: Групповые операции для повышения производительности

### 📱 Telegram API оптимизация
- **Inline-кнопки**: Быстрая навигация без перезагрузки интерфейса
- **Callback Queries**: Эффективная обработка пользовательских действий
- **Message Editing**: Обновление сообщений вместо отправки новых

### 🚀 Масштабируемость
- **Горизонтальное масштабирование**: Поддержка множественных экземпляров бота
- **Балансировка нагрузки**: Распределение запросов между серверами
- **Кэширование**: Redis для ускорения частых операций

## Установка и Запуск

### Требования
- Python 3.12+
- SQLAlchemy 2.0+
- PostgreSQL (рекомендуется), MySQL или SQLite

### Установка зависимостей
```bash
uv sync
```

### Настройка базы данных
```bash
# Для SQLite (по умолчанию)
python main.py

# Для PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost/events_bot"
python main.py

# Для MySQL
export DATABASE_URL="mysql://user:password@localhost/events_bot"
python main.py

# Для тестового бота (временная база в памяти)
TEST_MODE=true python test_bot.py

### 🐳 Docker

```bash
# Продакшн с PostgreSQL
docker-compose --profile production up -d

# Тестовый режим (без сохранения данных)
docker-compose --profile test up -d

# Podman (альтернатива Docker)
podman-compose --profile production up -d
```

## Структура проекта

```
events_bot/
├── events_bot/
│   ├── bot/
│   │   ├── handlers/          # Обработчики сообщений
│   │   │   ├── start_handler.py
│   │   │   ├── user_handlers.py
│   │   │   ├── post_handlers.py
│   │   │   ├── callback_handlers.py
│   │   │   └── moderation_handlers.py
│   │   ├── keyboards/         # Инлайн-клавиатуры
│   │   ├── states/           # FSM состояния
│   │   └── utils/            # Утилиты
│   └── database/
│       ├── models.py         # SQLAlchemy модели
│       ├── repositories/     # Слой доступа к данным
│       ├── services/         # Бизнес-логика
│       └── connection.py     # Подключение к БД
├── main.py                   # Точка входа
├── test_bot.py              # Тестовый бот
├── docker-compose.yaml      # Docker конфигурация
└── README.md               # Документация
```


```
- **Уведомления** - Автоматическая рассылка после одобрения

## API Основных Классов

### UserService (асинхронный)
- `register_user()` - Регистрация пользователя
- `select_categories()` - Выбор категорий
- `get_user_categories()` - Получение категорий пользователя

### PostService (асинхронный)
- `create_post()` - Создание поста
- `get_user_posts()` - Посты пользователя
- `get_posts_by_categories()` - Посты по нескольким категориям
- `approve_post()` - Одобрение поста
- `reject_post()` - Отклонение поста

### CategoryService (асинхронный)
- `get_all_categories()` - Все категории
- `get_category_by_id()` - Категория по ID

### ModerationService (асинхронный)
- `get_moderation_queue()` - Очередь модерации
- `format_post_for_moderation()` - Форматирование для модерации

### NotificationService (асинхронный)
- `get_users_to_notify()` - Пользователи для уведомления (по городу и категории)
- `format_post_notification()` - Форматирование уведомления

## Переменные Окружения

- `DATABASE_URL` - URL базы данных (автоматически преобразуется в асинхронный)
- `BOT_TOKEN` - Токен Telegram бота (обязательно)
- `MODERATION_GROUP_ID` - ID группы для модерации (обязательно)

### AWS S3 (при наличии данных авторизации)
- `S3_BUCKET_NAME` - Имя S3 bucket
- `AWS_ACCESS_KEY_ID` - AWS Access Key ID
- `AWS_SECRET_ACCESS_KEY` - AWS Secret Access Key
- `AWS_REGION` - AWS регион (по умолчанию us-east-1)
- `S3_ENDPOINT_URL` - URL эндпоинта (для совместимых сервисов)

### LocalStack (для разработки)
- `S3_BUCKET_NAME` - Имя S3 bucket (по умолчанию events-bot-uploads)
- `AWS_ACCESS_KEY_ID` - Тестовый ключ (по умолчанию test)
- `AWS_SECRET_ACCESS_KEY` - Тестовый секрет (по умолчанию test)
- `AWS_REGION` - Регион (по умолчанию us-east-1)
- `S3_ENDPOINT_URL` - URL LocalStack (по умолчанию http://localstack:4566)

## Поддерживаемые Базы Данных

- **PostgreSQL**: `postgresql://user:pass@host/db` → `postgresql+asyncpg://user:pass@host/db`
- **MySQL**: `mysql://user:pass@host/db` → `mysql+aiomysql://user:pass@host/db`
- **SQLite**: `sqlite:///./db.sqlite` → `sqlite+aiosqlite:///./db.sqlite`

## Файловое Хранилище

### Локальное хранилище (разработка)
- Файлы сохраняются в папку `uploads/`
- Подходит для разработки и тестирования

### S3 хранилище (при наличии данных авторизации)
- Файлы сохраняются в AWS S3
- Поддерживает временные URL для прямого доступа
- Автоматически выбирается при наличии переменных `S3_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Fallback на локальное хранилище при ошибках конфигурации

### LocalStack (разработка)
- Локальная эмуляция AWS S3 для разработки
- Полная совместимость с AWS S3 API
- Не требует реальных AWS учетных данных
- Автоматически запускается в docker-compose-dev.yaml

## Пример Mapped Стиля

```python
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    
    # Типизированные поля
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Типизированные связи
    posts: Mapped[List["Post"]] = relationship(back_populates="author")
```

## Запуск Бота

### Локальный запуск

1. **Установите зависимости:**
   ```bash
   uv sync
   ```

2. **Настройте переменные окружения:**
   ```bash
   export BOT_TOKEN="your_telegram_bot_token"
   export DATABASE_URL="sqlite+aiosqlite:///./events_bot.db"  # или другая БД
   ```

3. **Запустите бота:**
   ```bash
   uv run python main.py
   ```

### Docker запуск

#### Разработка (с локальной базой данных)

1. **Скопируйте пример переменных окружения:**
   ```bash
   cp env.example .env
   ```

2. **Отредактируйте .env файл:**
   ```bash
   nano .env
   ```

#### Продакшн (только бот)

1. **Скопируйте пример переменных окружения для продакшена:**
   ```bash
   cp env.production.example .env
   ```

2. **Отредактируйте .env файл с продакшн настройками:**
   ```bash
   nano .env
   ```

3. **Запустите полную среду разработки (PostgreSQL + Redis + LocalStack + Бот):**
   ```bash
   docker-compose -f docker-compose-dev.yaml up -d
   ```

4. **Запустите только тестовую версию с SQLite:**
   ```bash
   docker-compose -f docker-compose-dev.yaml --profile test up bot-test
   ```

**Примечание:** В development окружении используются порты:
- PostgreSQL: 5433 (вместо стандартного 5432)
- Redis: 6380 (вместо стандартного 6379)
- LocalStack: 4566

**Автоматическая инициализация S3:**
- Bucket `events-bot-uploads` создается автоматически при запуске LocalStack
- CORS настраивается автоматически
- Скрипты находятся в папке `aws/`

**Проверка S3 bucket:**
```bash
docker exec events_bot_localstack ./aws/check-buckets.sh
```

#### Продакшн (только бот)

1. **Настройте внешнюю базу данных и переменные окружения:**
   ```bash
   # Обязательные переменные
   export DATABASE_URL="postgresql+asyncpg://user:password@host:5432/dbname"
   export BOT_TOKEN="your_bot_token"
   export LOGFIRE_TOKEN="your_logfire_token"
   export MODERATION_GROUP_ID="your_moderation_group_id"
   
   # AWS S3 Configuration (опционально, для хранения картинок)
   export S3_BUCKET_NAME="your-s3-bucket-name"
   export AWS_ACCESS_KEY_ID="your-aws-access-key-id"
   export AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"
   export AWS_REGION="us-east-1"
   export S3_ENDPOINT_URL=""  # Оставьте пустым для AWS S3
   ```

2. **Запустите только бота:**
   ```bash
   docker-compose up -d
   ```

### Docker/Podman команды

- **Сборка образа:**
  ```bash
  docker build -t events-bot .
  ```

- **Запуск только бота (продакшн):**
  ```bash
  docker run --env-file .env -v uploads_data:/app/uploads events-bot
  ```

- **Просмотр логов:**
  ```bash
  docker-compose logs -f bot
  ```

- **Остановка:**
  ```bash
  docker-compose down
  ```

### Совместимость

Команды работают как с Docker, так и с Podman:
- `docker-compose` → `podman-compose`
- `docker build` → `podman build`
- `docker run` → `podman run`

## Производительность

- **Асинхронные операции**: Все операции с БД выполняются асинхронно
- **Connection pooling**: Автоматическое управление пулом соединений
- **Lazy loading**: Оптимизированная загрузка связанных объектов
- **Batch operations**: Поддержка пакетных операций

## Лицензия

MIT License
