from .connection import create_async_engine_and_session, create_tables
from .repositories import CategoryRepository
import logfire


async def init_database():
    """Асинхронная инициализация базы данных с примерами категорий"""
    engine, session_maker = create_async_engine_and_session()

    # Создаем таблицы
    try:
        await create_tables(engine)
        logfire.info("✅ Таблицы успешно созданы")
    except Exception as e:
        logfire.error(f"❌ Ошибка создания таблиц: {e}")
        raise

    # Создаем сессию для добавления данных
    async with session_maker() as db:
        try:
            # Проверяем, есть ли уже категории
            existing_categories = await CategoryRepository.get_all_active(db)
            if not existing_categories:
                # Создаем примеры категорий
                categories_data = [
                    {
                        "name": "Технологии",
                        "description": "Новости и обсуждения в сфере технологий",
                    },
                    {"name": "Спорт", "description": "Спортивные новости и события"},
                    {
                        "name": "Культура",
                        "description": "Культурные события и искусство",
                    },
                    {"name": "Наука", "description": "Научные открытия и исследования"},
                    {"name": "Бизнес", "description": "Бизнес новости и экономика"},
                    {
                        "name": "Здоровье",
                        "description": "Медицина и здоровый образ жизни",
                    },
                    {
                        "name": "Образование",
                        "description": "Образовательные программы и курсы",
                    },
                    {"name": "Путешествия", "description": "Туризм и путешествия"},
                    {
                        "name": "Кулинария",
                        "description": "Рецепты и кулинарные новости",
                    },
                    {"name": "Авто", "description": "Автомобильная тематика"},
                    {"name": "Мода", "description": "Модные тренды и стиль"},
                    {"name": "Музыка", "description": "Музыкальные новости и события"},
                    {"name": "Кино", "description": "Фильмы, сериалы и кинематограф"},
                    {"name": "Книги", "description": "Литература и книжные новинки"},
                    {"name": "Игры", "description": "Видеоигры и игровая индустрия"},
                ]

                for category_data in categories_data:
                    await CategoryRepository.create_category(
                        db,
                        name=category_data["name"],
                        description=category_data["description"],
                    )

                logfire.info("✅ База данных инициализирована с категориями!")
            else:
                logfire.info(
                    f"База данных уже содержит {len(existing_categories)} категорий"
                )

        except Exception as e:
            logfire.error(f"❌ Ошибка инициализации базы данных: {e}")
            await db.rollback()
            raise
