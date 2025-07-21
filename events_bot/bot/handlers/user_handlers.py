from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from events_bot.database.services import UserService, CategoryService, PostService
from events_bot.bot.states import UserStates
from events_bot.bot.keyboards import (
    get_main_keyboard,
    get_category_selection_keyboard,
    get_city_keyboard,
)

router = Router()


def register_user_handlers(dp: Router):
    """Регистрация обработчиков пользователя"""
    dp.include_router(router)


@router.message(F.text.in_(["/menu", "/main_menu"]))
async def cmd_main_menu(message: Message):
    """Обработчик команды /menu для главного меню"""
    menu_text = """
Главное меню
"""
    await message.answer(
        menu_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.text == "/my_posts")
async def cmd_my_posts(message: Message, db):
    """Обработчик команды /my_posts"""
    posts = await PostService.get_user_posts(db, message.from_user.id)

    if not posts:
        await message.answer(
            "📭 У вас пока нет постов.", reply_markup=get_main_keyboard()
        )
        return

    response = "📊 Ваши посты:\n\n"
    for post in posts:
        # Загружаем связанные объекты
        await db.refresh(post, attribute_names=["categories"])
        status = "✅ Одобрен" if post.is_approved else "⏳ На модерации"
        category_names = [cat.name for cat in post.categories] if post.categories else ['Неизвестно']
        category_str = ', '.join(category_names)
        post_city = getattr(post, 'city', 'Не указан')
        response += f"📝 {post.title}\n"
        response += f"🏙️ {post_city}\n"
        response += f"📂 {category_str}\n"
        response += f"📅 {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        response += f"📊 {status}\n\n"

    await message.answer(response, reply_markup=get_main_keyboard())


@router.message(F.text == "/change_city")
async def cmd_change_city(message: Message, state: FSMContext):
    """Обработчик команды /change_city"""
    await message.answer(
        "Выберите новый город:", reply_markup=get_city_keyboard()
    )
    await state.set_state(UserStates.waiting_for_city)


@router.message(F.text == "/change_category")
async def cmd_change_category(message: Message, state: FSMContext, db):
    """Обработчик команды /change_category"""
    categories = await CategoryService.get_all_categories(db)
    user_categories = await UserService.get_user_categories(
        db, message.from_user.id
    )
    selected_ids = [cat.id for cat in user_categories]

    await message.answer(
        "Выберите категории для публикации постов:",
        reply_markup=get_category_selection_keyboard(categories, selected_ids),
    )
    await state.set_state(UserStates.waiting_for_categories)


@router.message(F.text == "/help")
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
ℹ️ **Справка по боту**

🤖 **Основные функции:**
• /create_post - создание нового поста в выбранной категории
• /my_posts - просмотр ваших опубликованных постов
• /feed - просмотр ленты постов
• /moderation - доступ к модерации (для модераторов)
• /change_city - смена города для получения уведомлений
• /change_category - смена категории для публикации постов
• /menu - главное меню

📋 **Как использовать:**
1. Выберите город проживания
2. Выберите категорию для публикации постов
3. Создавайте посты в выбранной категории
4. Получайте уведомления о новых постах в вашем городе

📝 **Создание поста:**
• Заголовок: до 100 символов
• Содержание: до 2000 символов
• Посты проходят модерацию перед публикацией

❓ **Поддержка:** Обратитесь к администратору бота
"""

    await message.answer(
        help_text, reply_markup=get_main_keyboard(), parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("city_"))
async def process_city_selection_callback(callback: CallbackQuery, state: FSMContext, db):
    """Обработка выбора города через инлайн-кнопку"""
    city = callback.data[5:]

    # Обновляем город пользователя
    user = await UserService.register_user(
        db=db,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    user.city = city
    await db.commit()
    categories = await CategoryService.get_all_categories(db)
    await callback.message.edit_text(
        f"🏙️ Город {city} выбран!\n\nТеперь выберите категории для публикации постов:",
        reply_markup=get_category_selection_keyboard(categories),
    )
    await state.set_state(UserStates.waiting_for_categories)
    await callback.answer()


@router.callback_query(F.data == "change_city")
async def change_city_callback(callback: CallbackQuery, state: FSMContext):
    """Изменение города через инлайн-кнопку"""
    await callback.message.edit_text(
        "Выберите новый город:", reply_markup=get_city_keyboard()
    )
    await state.set_state(UserStates.waiting_for_city)
    await callback.answer()


@router.callback_query(F.data == "change_category")
async def change_category_callback(callback: CallbackQuery, state: FSMContext, db):
    """Изменение категории через инлайн-кнопку"""
    categories = await CategoryService.get_all_categories(db)
    user_categories = await UserService.get_user_categories(
        db, callback.from_user.id
    )
    selected_ids = [cat.id for cat in user_categories]

    await callback.message.edit_text(
        "Выберите категории для публикации постов:",
        reply_markup=get_category_selection_keyboard(categories, selected_ids),
    )
    await state.set_state(UserStates.waiting_for_categories)
    await callback.answer()


@router.callback_query(F.data == "my_posts")
async def show_my_posts_callback(callback: CallbackQuery, db):
    """Показать посты пользователя через инлайн-кнопку"""
    posts = await PostService.get_user_posts(db, callback.from_user.id)

    if not posts:
        await callback.message.edit_text(
            "📭 У вас пока нет постов.", reply_markup=get_main_keyboard()
        )
        return

    response = "📊 Ваши посты:\n\n"
    for post in posts:
        # Загружаем связанные объекты
        await db.refresh(post, attribute_names=["categories"])
        status = "✅ Одобрен" if post.is_approved else "⏳ На модерации"
        category_names = [cat.name for cat in post.categories] if post.categories else ['Неизвестно']
        category_str = ', '.join(category_names)
        post_city = getattr(post, 'city', 'Не указан')
        response += f"📝 {post.title}\n"
        response += f"🏙️ {post_city}\n"
        response += f"📂 {category_str}\n"
        response += f"📅 {post.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        response += f"📊 {status}\n\n"

    await callback.message.edit_text(response, reply_markup=get_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help_callback(callback: CallbackQuery):
    """Показать справку через инлайн-кнопку"""
    help_text = """
ℹ️ **Справка по боту**

🤖 **Основные функции:**
• 📝 Создать пост - создание нового поста в выбранной категории
• 📊 Мои посты - просмотр ваших опубликованных постов
• 🏙️ Изменить город - смена города для получения уведомлений
• 📂 Изменить категорию - смена категории для публикации постов
• 🏠 Главное меню - /menu

📋 **Как использовать:**
1. Выберите город проживания
2. Выберите категорию для публикации постов
3. Создавайте посты в выбранной категории
4. Получайте уведомления о новых постах в вашем городе

📝 **Создание поста:**
• Заголовок: до 200 символов
• Содержание: до 4000 символов
• Посты проходят модерацию перед публикацией

❓ **Поддержка:** Обратитесь к администратору бота
"""

    await callback.message.edit_text(
        help_text, reply_markup=get_main_keyboard(), parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def show_main_menu_callback(callback: CallbackQuery):
    """Обработчик кнопки возврата в главное меню"""
    menu_text = """
 *Главное меню*
"""
    await callback.message.edit_text(
        menu_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()
