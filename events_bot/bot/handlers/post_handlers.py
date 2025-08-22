import os
from datetime import datetime
from typing import Union

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
import logfire

from events_bot.bot.keyboards import (
    get_category_selection_keyboard,
    get_city_keyboard,
    get_main_keyboard,
)
from events_bot.bot.states import PostStates
from events_bot.database.services import CategoryService, PostService
from events_bot.storage import file_storage

# --- ИСПРАВЛЕНИЕ: Удален импорт loguru, проект стандартизирован на logfire ---
# from loguru import logger

router = Router()


def register_post_handlers(dp: Router):
    """Регистрация обработчиков постов"""
    dp.include_router(router)


@router.message(F.text == "/create_post")
@router.callback_query(F.data == "create_post")
async def start_post_creation(message_or_callback: Union[Message, CallbackQuery], state: FSMContext):
    """Начало процесса создания поста (через команду или инлайн-кнопку)"""
    user_id = message_or_callback.from_user.id
    logfire.info(f"Пользователь {user_id} начинает создание поста.")
    await state.clear()
    await state.set_state(PostStates.creating_post)
    
    text = "🏙️ Выберите город для вашего события:"
    reply_markup = get_city_keyboard(for_post=True)

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=reply_markup)
    else:
        await message_or_callback.message.edit_text(text, reply_markup=reply_markup)
        await message_or_callback.answer()
    
    await state.set_state(PostStates.waiting_for_city_selection)


@router.message(F.text == "/cancel")
@router.callback_query(F.data == "cancel_post")
async def cancel_post_creation(message_or_callback: Union[Message, CallbackQuery], state: FSMContext):
    """Отмена создания поста на любом этапе"""
    user_id = message_or_callback.from_user.id
    logfire.info(f"Пользователь {user_id} отменил создание поста.")
    await state.clear()
    
    text = "❌ Создание поста отменено."
    reply_markup = get_main_keyboard()

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=reply_markup)
    else:
        await message_or_callback.message.edit_text(text, reply_markup=reply_markup)
        await message_or_callback.answer()


@router.callback_query(PostStates.waiting_for_city_selection, F.data.startswith("post_city_"))
async def process_post_city_selection(callback: CallbackQuery, state: FSMContext, db):
    """Обработка выбора города для поста"""
    try:
        city = callback.data.split("_", 2)[2]
        logfire.info(f"Пользователь {callback.from_user.id} выбрал город: {city}")
        await state.update_data(post_city=city)
        
        all_categories = await CategoryService.get_all_categories(db)
        if not all_categories:
            await callback.message.edit_text("❌ Не удалось загрузить категории. Попробуйте позже.", reply_markup=get_main_keyboard())
            await state.clear()
            return

        await callback.message.edit_text(
            f"🏙️ Город «{city}» выбран.\n\n"
            f"📂 Теперь выберите одну или несколько подходящих категорий:",
            reply_markup=get_category_selection_keyboard(all_categories, for_post=True)
        )
        await state.set_state(PostStates.waiting_for_category_selection)
    except Exception as e:
        logfire.error(f"Ошибка при выборе города: {e}", exc_info=True)
        await callback.message.edit_text("❌ Произошла ошибка. Попробуйте начать заново.", reply_markup=get_main_keyboard())
        await state.clear()
    finally:
        await callback.answer()


@router.callback_query(PostStates.waiting_for_category_selection, F.data.startswith("post_category_"))
async def process_post_category_selection(callback: CallbackQuery, state: FSMContext, db):
    """Обработка выбора/отмены выбора категории"""
    try:
        category_id = int(callback.data.split("_")[2])
        data = await state.get_data()
        category_ids = data.get("category_ids", [])

        if category_id in category_ids:
            category_ids.remove(category_id)
        else:
            category_ids.append(category_id)
        await state.update_data(category_ids=category_ids)

        all_categories = await CategoryService.get_all_categories(db)
        await callback.message.edit_text(
            "📂 Выберите одну или несколько категорий. Нажмите «Подтвердить», когда закончите.",
            reply_markup=get_category_selection_keyboard(all_categories, category_ids, for_post=True)
        )
    except Exception as e:
        logfire.error(f"Ошибка при выборе категории: {e}", exc_info=True)
        await callback.message.edit_text("❌ Произошла ошибка. Попробуйте начать заново.", reply_markup=get_main_keyboard())
        await state.clear()
    finally:
        await callback.answer()


@router.callback_query(PostStates.waiting_for_category_selection, F.data == "confirm_post_categories")
async def confirm_post_categories(callback: CallbackQuery, state: FSMContext):
    """Подтверждение выбора категорий и переход к вводу заголовка"""
    try:
        data = await state.get_data()
        category_ids = data.get("category_ids", [])
        if not category_ids:
            await callback.answer("⚠️ Пожалуйста, выберите хотя бы одну категорию.", show_alert=True)
            return

        logfire.info(f"Пользователь {callback.from_user.id} подтвердил категории: {category_ids}")
        await callback.message.edit_text("📝 Отлично! Теперь введите заголовок вашего события:")
        await state.set_state(PostStates.waiting_for_title)
    except Exception as e:
        logfire.error(f"Ошибка при подтверждении категорий: {e}", exc_info=True)
    finally:
        await callback.answer()


@router.message(PostStates.waiting_for_title, F.text)
async def process_post_title(message: Message, state: FSMContext):
    """Обработка заголовка поста"""
    title = message.text.strip()
    # --- ИСПРАВЛЕНИЕ: Добавлена проверка на пустой ввод ---
    if not title:
        await message.answer("❌ Заголовок не может быть пустым. Пожалуйста, введите заголовок.")
        return
    if len(title) > 100:
        await message.answer("❌ Заголовок слишком длинный. Максимум 100 символов. Попробуйте снова.")
        return

    await state.update_data(title=title)
    logfire.info(f"Пользователь {message.from_user.id} ввел заголовок: {title}")
    await message.answer("📄 Теперь введите основной текст (описание) вашего события:")
    await state.set_state(PostStates.waiting_for_content)


@router.message(PostStates.waiting_for_content, F.text)
async def process_post_content(message: Message, state: FSMContext):
    """Обработка содержания поста"""
    content = message.text.strip()
    # --- ИСПРАВЛЕНИЕ: Добавлена проверка на пустой ввод ---
    if not content:
        await message.answer("❌ Описание не может быть пустым. Пожалуйста, введите текст.")
        return
    if len(content) > 2000:
        await message.answer("❌ Описание слишком длинное. Максимум 2000 символов. Попробуйте снова.")
        return

    await state.update_data(content=content)
    logfire.info(f"Пользователь {message.from_user.id} ввел описание поста.")
    await message.answer(
        "⏰ Введите дату и время окончания события в формате ДД.ММ.ГГГГ ЧЧ:ММ (например, 25.12.2024 18:30).\n"
        "После этого времени пост автоматически скроется из ленты."
    )
    await state.set_state(PostStates.waiting_for_event_datetime)


@router.message(PostStates.waiting_for_event_datetime, F.text)
async def process_event_datetime(message: Message, state: FSMContext):
    """Обработка даты и времени события"""
    try:
        event_dt = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        
        # --- ИСПРАВЛЕНИЕ: Добавлена проверка, что дата не в прошлом ---
        if event_dt <= datetime.now():
            await message.answer("❌ Дата и время не могут быть в прошлом. Пожалуйста, введите будущую дату.")
            return

        await state.update_data(event_at=event_dt.isoformat())
        logfire.info(f"Пользователь {message.from_user.id} установил дату события: {event_dt.isoformat()}")
        await message.answer("🖼️ Теперь отправьте изображение для афиши (или /skip, чтобы пропустить).")
        await state.set_state(PostStates.waiting_for_image)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ ЧЧ:ММ (например, 25.12.2024 18:30).")
    except Exception as e:
        logfire.error(f"Ошибка при обработке даты: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при обработке даты. Попробуйте еще раз.")


@router.message(PostStates.waiting_for_image, (F.photo | (F.text == "/skip")))
async def process_post_image(message: Message, state: FSMContext, db):
    """Обработка изображения для поста или его пропуск"""
    try:
        if message.text == "/skip":
            logfire.info(f"Пользователь {message.from_user.id} пропустил добавление изображения.")
            await state.update_data(image_id=None)
            await finalize_post_creation(message, state, db)
            return

        if message.photo:
            photo = message.photo[-1]
            file_info = await message.bot.get_file(photo.file_id)
            file_data = await message.bot.download_file(file_info.file_path)
            
            # --- ИСПРАВЛЕНИЕ: Расширение файла определяется автоматически, а не жестко задано как 'jpg' ---
            file_ext = os.path.splitext(file_info.file_path)[1]
            if not file_ext:
                file_ext = ".jpg" # Запасной вариант
            
            file_id = await file_storage.save_file(file_data.read(), file_ext.lstrip('.'))
            await state.update_data(image_id=file_id)
            logfire.info(f"Пользователь {message.from_user.id} загрузил изображение, ID файла: {file_id}")
            
            await finalize_post_creation(message, state, db)
        else:
             await message.answer("❌ Пожалуйста, отправьте именно изображение или нажмите /skip.")

    except Exception as e:
        logfire.error(f"Ошибка при обработке изображения: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при сохранении изображения. Попробуйте еще раз или пропустите этот шаг.", reply_markup=get_main_keyboard())
        await state.clear()


async def finalize_post_creation(message: Message, state: FSMContext, db):
    """Завершающий этап: сбор всех данных и отправка поста на модерацию"""
    user_id = message.from_user.id
    logfire.info(f"Завершение создания поста для пользователя {user_id}.")
    
    try:
        data = await state.get_data()
        
        # --- ИСПРАВЛЕНИЕ: Более надежная проверка данных перед созданием ---
        required_keys = ["title", "content", "category_ids", "post_city", "event_at"]
        if not all(key in data and data[key] for key in required_keys):
            missing_keys = [key for key in required_keys if key not in data or not data[key]]
            logfire.error(f"Ошибка: не все данные для поста заполнены для пользователя {user_id}. Отсутствуют: {missing_keys}")
            await message.answer(
                "❌ Критическая ошибка: не все данные поста были сохранены. Пожалуйста, начните создание поста заново.",
                reply_markup=get_main_keyboard(),
            )
            return

        post = await PostService.create_post_and_send_to_moderation(
            db=db,
            bot=message.bot,
            author_id=user_id,
            title=data["title"],
            content=data["content"],
            category_ids=data["category_ids"],
            city=data["post_city"],
            image_id=data.get("image_id"), # Может быть None
            event_at=data["event_at"],
        )

        if post:
            logfire.info(f"Пост {post.id} от пользователя {user_id} успешно создан и отправлен на модерацию.")
            await message.answer(
                "✅ Ваш пост успешно создан и отправлен на модерацию!",
                reply_markup=get_main_keyboard(),
            )
        else:
            raise Exception("PostService вернул None")

    except Exception as e:
        logfire.error(f"Критическая ошибка при создании поста для пользователя {user_id}: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла серьезная ошибка при создании поста. Пожалуйста, попробуйте еще раз.",
            reply_markup=get_main_keyboard(),
        )
    finally:
        await state.clear()