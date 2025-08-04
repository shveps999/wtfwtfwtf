from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from typing import Union
import logfire
from datetime import datetime

from events_bot.database.services import PostService, UserService, CategoryService
from events_bot.bot.states import PostStates
from events_bot.bot.keyboards import (
    get_main_keyboard,
    get_city_keyboard,
    get_category_selection_keyboard,
)
from events_bot.storage import file_storage
from loguru import logger

router = Router()


@router.message(F.text == "/create_post")
async def cmd_create_post(message: Message, state: FSMContext, db):
    await state.set_state(PostStates.creating_post)
    await message.answer("🏙️ Выберите город для поста:", reply_markup=get_city_keyboard(for_post=True))


@router.callback_query(PostStates.waiting_for_city_selection, F.data.startswith("post_city_"))
async def process_post_city_selection(callback: CallbackQuery, state: FSMContext, db):
    city = callback.data[10:]
    await state.update_data(post_city=city)
    all_categories = await CategoryService.get_all_categories(db)
    await callback.message.edit_text(
        f"🏙️ Город {city} выбран!\n📂 Теперь выберите категории для поста:",
        reply_markup=get_category_selection_keyboard(all_categories, for_post=True)
    )
    await state.set_state(PostStates.waiting_for_category_selection)
    await callback.answer()


@router.callback_query(PostStates.waiting_for_category_selection, F.data.startswith("post_category_"))
async def process_post_category_selection(callback: CallbackQuery, state: FSMContext, db):
    category_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    category_ids = data.get("category_ids", [])

    if category_id in category_ids:
        category_ids.remove(category_id)
    else:
        category_ids.append(category_id)

    await state.update_data(category_ids=category_ids)
    all_categories = await CategoryService.get_all_categories(db)
    keyboard = get_category_selection_keyboard(all_categories, selected_ids=category_ids, for_post=True)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@router.callback_query(PostStates.waiting_for_category_selection, F.data == "post_categories_done")
async def process_categories_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("category_ids"):
        await callback.answer("❌ Выберите хотя бы одну категорию!")
        return
    await callback.message.edit_text("📝 Введите заголовок поста:")
    await state.set_state(PostStates.waiting_for_title)
    await callback.answer()


@router.message(PostStates.waiting_for_title)
async def process_post_title(message: Message, state: FSMContext, db):
    if len(message.text) > 100:
        await message.answer("❌ Заголовок слишком длинный. Максимум 100 символов.")
        return
    await state.update_data(title=message.text)
    await message.answer("📄 Введите содержание поста:")
    await state.set_state(PostStates.waiting_for_content)


@router.message(PostStates.waiting_for_content)
async def process_post_content(message: Message, state: FSMContext):
    if len(message.text) > 2000:
        await message.answer("❌ Содержание слишком длинное. Максимум 2000 символов.")
        return
    await state.update_data(content=message.text)
    await message.answer("📅 Введите дату события в формате ДД.ММ.ГГГГ (например, 05.09.2025):")
    await state.set_state(PostStates.waiting_for_event_date)


@router.message(PostStates.waiting_for_event_date)
async def process_event_date(message: Message, state: FSMContext):
    date_text = message.text.strip()
    try:
        event_date = datetime.strptime(date_text, "%d.%m.%Y").date()
        await state.update_data(event_date=event_date)
        await message.answer("⏰ Введите время события в формате ЧЧ:ММ (например, 15:30):")
        await state.set_state(PostStates.waiting_for_event_time)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ.")
        return


@router.message(PostStates.waiting_for_event_time)
async def process_event_time(message: Message, state: FSMContext, db):
    time_text = message.text.strip()
    try:
        event_time = datetime.strptime(time_text, "%H:%M").time()
        data = await state.get_data()
        event_datetime = datetime.combine(data["event_date"], event_time)

        if event_datetime <= datetime.now(event_datetime.tzinfo):
            await message.answer("❌ Дата и время события должны быть в будущем.")
            return

        await state.update_data(event_datetime=event_datetime)
        await message.answer("🖼️ Отправьте изображение для поста (или нажмите /skip для пропуска):")
        await state.set_state(PostStates.waiting_for_image)
    except ValueError:
        await message.answer("❌ Неверный формат времени. Введите в формате ЧЧ:ММ.")
        return


@router.message(PostStates.waiting_for_image)
async def process_post_image(message: Message, state: FSMContext, db):
    if message.text == "/skip":
        await continue_post_creation(message, state, db)
        return
    if not message.photo:
        await message.answer("❌ Пожалуйста, отправьте изображение или нажмите /skip")
        return

    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)
    file_data = await message.bot.download_file(file_info.file_path)
    file_id = await file_storage.save_file(file_data.read(), 'jpg')
    await state.update_data(image_id=file_id)
    await continue_post_creation(message, state, db)


async def continue_post_creation(message: Message, state: FSMContext, db):
    user_id = message.from_user.id
    data = await state.get_data()

    category_ids = data.get("category_ids", [])
    post_city = data.get("post_city")
    event_datetime = data.get("event_datetime")

    post = await PostService.create_post_and_send_to_moderation(
        db=db,
        title=data["title"],
        content=data["content"],
        author_id=user_id,
        category_ids=category_ids,
        city=post_city,
        image_id=data.get("image_id"),
        event_datetime=event_datetime,
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
