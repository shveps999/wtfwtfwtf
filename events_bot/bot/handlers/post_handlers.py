from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from typing import Union
import logfire
from events_bot.database.services import PostService, UserService, CategoryService
from events_bot.bot.states import PostStates
from events_bot.bot.keyboards import (
    get_main_keyboard,
    get_category_selection_keyboard,
    get_city_keyboard,
)
from events_bot.storage import file_storage
from loguru import logger

router = Router()


def register_post_handlers(dp: Router):
    """Регистрация обработчиков постов"""
    dp.include_router(router)


@router.message(F.text == "/create_post")
async def cmd_create_post(message: Message, state: FSMContext, db):
    """Обработчик команды /create_post"""
    # Устанавливаем начальное состояние создания поста
    await state.set_state(PostStates.creating_post)
    
    # Сначала предлагаем выбрать город
    await message.answer(
        "🏙️ Выберите город для поста:",
        reply_markup=get_city_keyboard(for_post=True)
    )
    await state.set_state(PostStates.waiting_for_city_selection)


@router.message(F.text == "/cancel")
async def cmd_cancel_post(message: Message, state: FSMContext, db):
    """Отмена создания поста на любом этапе"""
    logfire.info(f"Пользователь {message.from_user.id} отменил создание поста")
    await state.clear()
    await message.answer(
        "❌ Создание поста отменено.",
        reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "create_post")
async def start_create_post(callback: CallbackQuery, state: FSMContext, db):
    """Начать создание поста через инлайн-кнопку"""
    # Устанавливаем начальное состояние создания поста
    await state.set_state(PostStates.creating_post)
    
    # Сначала предлагаем выбрать город
    await callback.message.edit_text(
        "🏙️ Выберите город для поста:",
        reply_markup=get_city_keyboard(for_post=True)
    )
    await state.set_state(PostStates.waiting_for_city_selection)
    await callback.answer()


@router.callback_query(F.data == "cancel_post")
async def cancel_post_creation(callback: CallbackQuery, state: FSMContext, db):
    """Отмена создания поста"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Создание поста отменено.",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@router.callback_query(PostStates.waiting_for_city_selection, F.data.startswith("post_city_"))
async def process_post_city_selection(callback: CallbackQuery, state: FSMContext, db):
    """Обработка выбора города для поста"""
    city = callback.data[10:]  # Убираем префикс "post_city_"

    # Сохраняем выбранный город
    await state.update_data(post_city=city)
    
    # Получаем все категории для выбора
    all_categories = await CategoryService.get_all_categories(db)
    
    await callback.message.edit_text(
        f"🏙️ Город {city} выбран!\n\n📂 Теперь выберите категории для поста:",
        reply_markup=get_category_selection_keyboard(all_categories, for_post=True)
    )
    await state.set_state(PostStates.waiting_for_category_selection)
    await callback.answer()


@router.callback_query(PostStates.waiting_for_category_selection, F.data.startswith("post_category_"))
async def process_post_category_selection(callback: CallbackQuery, state: FSMContext, db):
    """Мультивыбор категорий для поста"""
    category_id = int(callback.data.split("_")[2])  # post_category_123 -> 123
    data = await state.get_data()
    category_ids = data.get("category_ids", [])

    if category_id in category_ids:
        category_ids.remove(category_id)
    else:
        category_ids.append(category_id)
    await state.update_data(category_ids=category_ids)

    # Получаем все категории для выбора
    all_categories = await CategoryService.get_all_categories(db)
    await callback.message.edit_text(
        "📂 Выберите одну или несколько категорий для поста (можно выбрать несколько):",
        reply_markup=get_category_selection_keyboard(all_categories, category_ids, for_post=True)
    )
    await callback.answer()

@router.callback_query(PostStates.waiting_for_category_selection, F.data == "confirm_post_categories")
@logger.catch
async def confirm_post_categories(callback: CallbackQuery, state: FSMContext, db):
    """Подтверждение выбора категорий для поста"""
    data = await state.get_data()
    category_ids = data.get("category_ids", [])
    if not category_ids:
        await callback.answer("Выберите хотя бы одну категорию", show_alert=True)
        return
    await state.update_data(category_ids=category_ids)
    logfire.info(f"Категории подтверждены для пользователя {callback.from_user.id}: {category_ids}")
    await callback.message.edit_text(
        f"📝 Создание поста в категориях: {len(category_ids)} выбрано\n\nВведите заголовок поста:"
    )
    await state.set_state(PostStates.waiting_for_title)
    logfire.info(f"Состояние изменено на waiting_for_title для пользователя {callback.from_user.id}")
    await callback.answer()

@router.message(PostStates.waiting_for_title)
@logger.catch
async def process_post_title(message: Message, state: FSMContext, db):
    """Обработка заголовка поста"""
    logfire.info(f"Получен заголовок поста от пользователя {message.from_user.id}: {message.text}")
    
    if len(message.text) > 100:
        await message.answer("❌ Заголовок слишком длинный. Максимум 100 символов.")
        return

    await state.update_data(title=message.text)
    logfire.info(f"Заголовок сохранен в состоянии: {message.text}")
    await message.answer("📄 Введите содержание поста:")
    await state.set_state(PostStates.waiting_for_content)
    logfire.info(f"Состояние изменено на waiting_for_content для пользователя {message.from_user.id}")


@router.message(PostStates.waiting_for_content)
async def process_post_content(message: Message, state: FSMContext, db):
    """Обработка содержания поста"""
    if len(message.text) > 2000:
        await message.answer("❌ Содержание слишком длинное. Максимум 2000 символов.")
        return

    await state.update_data(content=message.text)
    await message.answer(
        "⏰ Введите дату и время события в формате ДД.ММ.ГГГГ ЧЧ:ММ (например, 25.12.2025 18:30):\n"
        "После наступления этого времени пост будет скрыт из ленты и удалён."
    )
    await state.set_state(PostStates.waiting_for_event_datetime)


@router.message(PostStates.waiting_for_event_datetime)
async def process_event_datetime(message: Message, state: FSMContext, db):
    """Обработка даты/времени события"""
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
    except Exception:
        ZoneInfo = None
    text = message.text.strip()
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y %H.%M"):
        try:
            event_dt = datetime.strptime(text, fmt)
            # Считаем введённое время в часовом поясе МСК
            if ZoneInfo is not None:
                msk = ZoneInfo("Europe/Moscow")
                utc = ZoneInfo("UTC")
                event_dt = event_dt.replace(tzinfo=msk).astimezone(utc)
            # Сохраняем в ISO (с таймзоной +00:00)
            await state.update_data(event_at=event_dt.isoformat())
            await message.answer(
                "🖼️ Отправьте изображение для поста (или нажмите /skip для пропуска):"
            )
            await state.set_state(PostStates.waiting_for_image)
            return
        except ValueError:
            continue
    await message.answer("❌ Неверный формат. Пример: 25.12.2025 18:30. Попробуйте снова.")


@router.message(PostStates.waiting_for_image)
async def process_post_image(message: Message, state: FSMContext, db):
    """Обработка изображения поста"""
    if message.text == "/skip":
        await continue_post_creation(message, state, db)
        return

    if not message.photo:
        await message.answer("❌ Пожалуйста, отправьте изображение или нажмите /skip")
        return

    # Получаем самое большое изображение
    photo = message.photo[-1]
    
    # Скачиваем файл
    file_info = await message.bot.get_file(photo.file_id)
    file_data = await message.bot.download_file(file_info.file_path)
    
    # Сохраняем файл
    file_id = await file_storage.save_file(file_data.read(), 'jpg')
    
    await state.update_data(image_id=file_id)
    await continue_post_creation(message, state, db)


@router.callback_query(PostStates.waiting_for_image, F.data == "skip_image")
async def skip_image_callback(callback: CallbackQuery, state: FSMContext, db):
    await continue_post_creation(callback, state, db)


async def continue_post_creation(callback_or_message: Union[Message, CallbackQuery], state: FSMContext, db):
    """Продолжение создания поста после загрузки изображения"""
    user_id = callback_or_message.from_user.id
    message = callback_or_message if isinstance(callback_or_message, Message) else callback_or_message.message
    data = await state.get_data()
    title = data.get("title")
    content = data.get("content")
    category_ids = data.get("category_ids", [])
    post_city = data.get("post_city")
    image_id = data.get("image_id")
    event_at_iso = data.get("event_at")

    if not all([title, content, category_ids, post_city]):
        await message.answer(
            "❌ Ошибка: не все данные поста заполнены. Попробуйте создать пост заново.",
            reply_markup=get_main_keyboard(),
        )
        await state.clear()
        return

    # Создаем один пост с несколькими категориями
    post = await PostService.create_post_and_send_to_moderation(
        db=db,
        title=title,
        content=content,
        author_id=user_id,
        category_ids=category_ids,
        city=post_city,
        image_id=image_id,
        event_at=event_at_iso,
        bot=message.bot
    )

    if post:
        await message.answer(
            f"✅ Пост создан и отправлен на модерацию в городе {post_city} в {len(category_ids)} категориях!",
            reply_markup=get_main_keyboard(),
        )
        await state.clear()
    else:
        await message.answer(
            "❌ Ошибка при создании поста. Попробуйте еще раз.",
            reply_markup=get_main_keyboard(),
        )
        await state.clear()
