from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logfire
from events_bot.database.services import (
    ModerationService,
    PostService,
    NotificationService,
)
from events_bot.bot.utils import send_post_notification
from events_bot.storage import file_storage
from events_bot.database.models import ModerationAction
from events_bot.bot.keyboards import (
    get_moderation_keyboard,
    get_moderation_queue_keyboard,
    get_main_keyboard,
)
from events_bot.bot.states.moderation_states import ModerationStates

router = Router()


def register_moderation_handlers(dp: Router):
    """Регистрация обработчиков модерации"""
    dp.include_router(router)


@router.message(F.text == "/moderation")
async def cmd_moderation(message: Message, db):
    """Обработчик команды /moderation"""
    logfire.info(f"Пользователь {message.from_user.id} запросил модерацию через команду")
    pending_posts = await ModerationService.get_moderation_queue(db)

    if not pending_posts:
        logfire.info("Очередь модерации пуста")
        await message.answer(
            "Нет постов на модерации.",
            reply_markup=get_main_keyboard(),
        )
        return

    logfire.info(f"Найдено {len(pending_posts)} постов на модерации")
    response = "Посты на модерации:\n\n"
    for post in pending_posts:
        await db.refresh(post, attribute_names=["author", "categories"])
        category_names = [cat.name for cat in post.categories] if post.categories else ['Неизвестно']
        category_str = ', '.join(category_names)
        post_city = getattr(post, 'city', 'Не указан')
        response += f"{post.title}\n"
        response += f"Город: {post_city}\n"
        response += f"{post.author.first_name or post.author.username}\n"
        response += f"{category_str}\n"
        response += f"ID: {post.id}\n\n"

    await message.answer(
        response, reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "moderation")
async def show_moderation_queue_callback(callback: CallbackQuery, db):
    """Показать очередь модерации через инлайн-кнопку"""
    logfire.info(f"Пользователь {callback.from_user.id} запросил очередь модерации")
    pending_posts = await ModerationService.get_moderation_queue(db)

    if not pending_posts:
        logfire.info("Очередь модерации пуста")
        await callback.message.edit_text(
            "Нет постов на модерации.",
            reply_markup=get_moderation_queue_keyboard(),
        )
        return

    logfire.info(f"Найдено {len(pending_posts)} постов на модерации")
    response = "Посты на модерации:\n\n"
    for post in pending_posts:
        await db.refresh(post, attribute_names=["author", "categories"])
        category_names = [cat.name for cat in post.categories] if post.categories else ['Неизвестно']
        category_str = ', '.join(category_names)
        post_city = getattr(post, 'city', 'Не указан')
        response += f"{post.title}\n"
        response += f"Город: {post_city}\n"
        response += f"{post.author.first_name or post.author.username}\n"
        response += f"{category_str}\n"
        response += f"ID: {post.id}\n\n"

    await callback.message.edit_text(
        response, reply_markup=get_moderation_queue_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "refresh_moderation")
async def refresh_moderation_queue(callback: CallbackQuery, db):
    """Обновить очередь модерации"""
    logfire.info(f"Пользователь {callback.from_user.id} обновил очередь модерации")
    pending_posts = await ModerationService.get_moderation_queue(db)

    if not pending_posts:
        logfire.info("Очередь модерации пуста при обновлении")
        await callback.message.edit_text(
            "Нет постов на модерации.",
            reply_markup=get_moderation_queue_keyboard(),
        )
        await callback.answer("Очередь обновлена")
        return

    logfire.info(f"Обновлено: найдено {len(pending_posts)} постов на модерации")
    response = "Посты на модерации:\n\n"
    for post in pending_posts:
        await db.refresh(post, attribute_names=["author", "categories"])
        category_names = [cat.name for cat in post.categories] if post.categories else ['Неизвестно']
        category_str = ', '.join(category_names)
        post_city = getattr(post, 'city', 'Не указан')
        response += f"{post.title}\n"
        response += f"Город: {post_city}\n"
        response += f"{post.author.first_name or post.author.username}\n"
        response += f"{category_str}\n"
        response += f"ID: {post.id}\n\n"

    await callback.message.edit_text(
        response, reply_markup=get_moderation_queue_keyboard()
    )
    await callback.answer("Очередь обновлена")


@router.callback_query(F.data.startswith("moderate_"))
async def process_moderation_action(callback: CallbackQuery, state: FSMContext, db):
    """Обработка действий модерации"""
    data = callback.data.split("_")
    action = data[1]
    post_id = int(data[2])
    
    logfire.info(f"Модератор {callback.from_user.id} выполняет действие {action} для поста {post_id}")

    if action == "approve":
        post = await PostService.approve_post(db, post_id, callback.from_user.id)
        if post:
            # Публикуем пост
            post = await PostService.publish_post(db, post_id)
            await db.refresh(post, attribute_names=["author", "categories"])
            logfire.info(f"Пост {post_id} одобрен и опубликован модератором {callback.from_user.id}")
            
            # Отправляем уведомления пользователям
            users_to_notify = await NotificationService.get_users_to_notify(
                db, post
            )
            logfire.info(f"Отправляем уведомления {len(users_to_notify)} пользователям")
            await send_post_notification(callback.bot, post, users_to_notify, db)

            # Уведомляем автора
            try:
                await callback.bot.send_message(chat_id=post.author_id, text=f"✅ Ваш пост '{post.title}' одобрен и опубликован!")
            except Exception:
                pass

            await callback.answer("✅ Пост одобрен и опубликован!")
            await callback.message.delete()
        else:
            logfire.error(f"Ошибка при одобрении поста {post_id}")
            await callback.answer("❌ Ошибка при одобрении поста")

    elif action == "reject":
        # спрашиваем комментарий у модератора, сохраняя post_id и тип действия
        await state.update_data(pending_post_id=post_id, pending_action="reject")
        await state.set_state(ModerationStates.waiting_for_comment)
        await callback.message.edit_text("❌ Укажите причину отклонения (комментарий для автора):")
        await callback.answer()

    elif action == "changes":
        # спрашиваем комментарий у модератора, сохраняя post_id в FSM
        await state.update_data(pending_post_id=post_id)
        await state.set_state(ModerationStates.waiting_for_comment)
        await callback.message.edit_text("📝 Введите комментарий для автора (что исправить):")
        await callback.answer()


@router.message(ModerationStates.waiting_for_comment)
async def receive_moderator_comment(message: Message, state: FSMContext, db):
    data = await state.get_data()
    post_id = data.get("pending_post_id")
    pending_action = data.get("pending_action", "changes")
    comment = message.text.strip()
    if not post_id:
        await message.answer("Не удалось определить пост. Попробуйте снова.")
        await state.clear()
        return
    if pending_action == "reject":
        post = await PostService.reject_post(db, post_id, message.from_user.id, comment)
        if post:
            await message.answer("❌ Пост отклонён. Комментарий отправлен автору.")
            try:
                await message.bot.send_message(chat_id=post.author_id, text=f"❌ Ваш пост '{post.title}' отклонён. Комментарий модератора: {comment}")
            except Exception:
                pass
        else:
            await message.answer("❌ Ошибка при отклонении поста")
    else:
        post = await PostService.request_changes(db, post_id, message.from_user.id, comment)
        if post:
            await message.answer("📝 Запрошены изменения. Комментарий отправлен автору.")
            # Уведомим автора
            try:
                await message.bot.send_message(chat_id=post.author_id, text=f"📝 Ваш пост '{post.title}' требует изменений. Комментарий модератора: {comment}")
            except Exception:
                pass
        else:
            await message.answer("❌ Ошибка при запросе изменений")
    await state.clear()
