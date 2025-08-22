import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logfire

from events_bot.database.services import (
    ModerationService,
    PostService,
    NotificationService,
)
from events_bot.bot.utils import send_post_notification
from events_bot.database.models import ModerationAction
from events_bot.bot.keyboards import (
    get_main_keyboard,
    get_moderation_queue_keyboard,
)
from events_bot.bot.states.moderation_states import ModerationStates

# --- ИСПРАВЛЕНИЕ: MODERATION_GROUP_ID считывается из переменной окружения ---
# Команды модерации от чатов, не имеющих этого ID, будут блокироваться.
# Убедитесь, что вы определили MODERATION_GROUP_ID в вашем .env файле.
# Пример: MODERATION_GROUP_ID=-100123456789
try:
    MODERATION_GROUP_ID = int(os.getenv("MODERATION_GROUP_ID", 0))
    if MODERATION_GROUP_ID == 0:
        logfire.warning("Переменная окружения MODERATION_GROUP_ID не установлена. Функции модерации могут не работать.")
except (ValueError, TypeError):
    logfire.error("MODERATION_GROUP_ID имеет неверное значение. Оно должно быть целым числом.")
    MODERATION_GROUP_ID = 0


router = Router()

# --- ИСПРАВЛЕНИЕ: Все обработчики защищены фильтром на уровне роутера ---
# Обрабатываются только сообщения и колбэки из указанной группы модерации.
if MODERATION_GROUP_ID:
    router.message.filter(F.chat.id == MODERATION_GROUP_ID)
    router.callback_query.filter(F.message.chat.id == MODERATION_GROUP_ID)


def register_moderation_handlers(dp: Router):
    """Регистрация обработчиков модерации"""
    dp.include_router(router)


@router.message(Command("moderation"))
async def cmd_moderation(message: Message, db):
    """Обработчик команды /moderation"""
    logfire.info(f"Пользователь {message.from_user.id} запросил очередь модерации через команду.")
    
    try:
        pending_posts = await ModerationService.get_moderation_queue(db)

        if not pending_posts:
            logfire.info("Очередь модерации пуста.")
            await message.answer(
                "Нет постов на модерации.",
                reply_markup=get_main_keyboard(),
            )
            return

        logfire.info(f"Найдено {len(pending_posts)} постов на модерации.")
        response = "Посты на модерации:\n\n"
        for post in pending_posts:
            # --- ИСПРАВЛЕНИЕ: Ненужный вызов db.refresh удален ---
            # Связанные данные (автор, категории) должны быть загружены в сервисе.
            category_names = [cat.name for cat in post.categories] if hasattr(post, 'categories') else ['Неизвестно']
            category_str = ', '.join(category_names)
            author_name = post.author.first_name or post.author.username if hasattr(post, 'author') else 'Неизвестно'
            post_city = getattr(post, 'city', 'Не указан')

            response += f"Заголовок: {post.title}\n"
            response += f"Город: {post_city}\n"
            response += f"Автор: {author_name}\n"
            response += f"Категории: {category_str}\n"
            response += f"ID: `{post.id}`\n\n"

        # Контроль длины сообщения
        if len(response) > 4096:
            response = response[:4090] + "\n..."
        
        await message.answer(response, reply_markup=get_main_keyboard(), parse_mode="MarkdownV2")
    except Exception as e:
        logfire.error(f"Ошибка при получении очереди модерации: {e}", exc_info=True)
        await message.answer("❌ Произошла ошибка при получении очереди модерации.")


@router.callback_query(F.data.in_({"moderation", "refresh_moderation"}))
async def show_moderation_queue_callback(callback: CallbackQuery, db):
    """Показать или обновить очередь модерации через инлайн-кнопку"""
    logfire.info(f"Пользователь {callback.from_user.id} запросил/обновил очередь модерации.")
    
    try:
        pending_posts = await ModerationService.get_moderation_queue(db)

        if not pending_posts:
            logfire.info("Очередь модерации пуста.")
            await callback.message.edit_text(
                "Нет постов на модерации.",
                reply_markup=get_moderation_queue_keyboard(),
            )
            await callback.answer("Очередь пуста.")
            return

        logfire.info(f"Найдено {len(pending_posts)} постов на модерации.")
        response = "Посты на модерации:\n\n"
        for post in pending_posts:
            # --- ИСПРАВЛЕНИЕ: Ненужный вызов db.refresh удален ---
            category_names = [cat.name for cat in post.categories] if hasattr(post, 'categories') else ['Неизвестно']
            category_str = ', '.join(category_names)
            author_name = post.author.first_name or post.author.username if hasattr(post, 'author') else 'Неизвестно'
            post_city = getattr(post, 'city', 'Не указан')

            response += f"Заголовок: {post.title}\n"
            response += f"Город: {post_city}\n"
            response += f"Автор: {author_name}\n"
            response += f"Категории: {category_str}\n"
            response += f"ID: `{post.id}`\n\n"

        if len(response) > 4096:
            response = response[:4090] + "\n..."
        
        await callback.message.edit_text(
            response, reply_markup=get_moderation_queue_keyboard(), parse_mode="MarkdownV2"
        )
        if callback.data == "refresh_moderation":
            await callback.answer("✅ Очередь обновлена.")
        else:
            await callback.answer()
            
    except TelegramBadRequest:
        logfire.warning("Получена ошибка TelegramBadRequest, т.к. сообщение не изменилось.")
        await callback.answer("ℹ️ Содержимое уже актуально.")
    except Exception as e:
        logfire.error(f"Ошибка при отображении очереди модерации: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка.", show_alert=True)


@router.callback_query(F.data.startswith("moderate_"))
async def process_moderation_action(callback: CallbackQuery, state: FSMContext, db):
    """Обработка действий модерации (одобрить, отклонить, запросить изменения)"""
    await callback.answer()
    try:
        _, action, post_id_str = callback.data.split("_", 2)
        post_id = int(post_id_str)
    except ValueError:
        logfire.error(f"Неверные данные в callback: {callback.data}")
        await callback.message.edit_text("❌ Неверные данные для операции.")
        return

    logfire.info(f"Модератор {callback.from_user.id} выполняет действие '{action}' для поста {post_id}.")

    try:
        if action == "approve":
            post = await PostService.approve_post(db, post_id, callback.from_user.id)
            if post:
                # --- ИСПРАВЛЕНИЕ: Ненужный db.refresh удален. Сервис должен возвращать актуальные данные. ---
                logfire.info(f"Пост {post_id} одобрен и будет опубликован.")
                
                # Отправка уведомлений
                users_to_notify = await NotificationService.get_users_to_notify(db, post)
                logfire.info(f"Отправка уведомлений {len(users_to_notify)} пользователям.")
                await send_post_notification(callback.bot, post, users_to_notify, db)

                # Уведомление автора
                try:
                    await callback.bot.send_message(
                        chat_id=post.author_id,
                        text=f"✅ Ваш пост '{post.title}' одобрен и опубликован!"
                    )
                except Exception as e:
                    logfire.warning(f"Не удалось уведомить автора {post.author_id}: {e}")

                await callback.message.delete()
            else:
                logfire.error(f"Ошибка при одобрении поста {post_id} или пост не найден.")
                await callback.message.edit_text("❌ Произошла ошибка при одобрении поста.")

        elif action in ("reject", "changes"):
            await state.update_data(pending_post_id=post_id, pending_action=action)
            await state.set_state(ModerationStates.waiting_for_comment)
            
            prompt_text = {
                "reject": "❌ Укажите причину отклонения (комментарий для автора):",
                "changes": "📝 Введите комментарий для автора (что исправить):",
            }
            await callback.message.edit_text(prompt_text[action])
        
        else:
            logfire.warning(f"Неизвестное действие модерации: {action}")
            await callback.message.edit_text("❌ Попытка выполнить неизвестное действие.")

    except Exception as e:
        logfire.error(f"Ошибка в процессе модерации: {e}", exc_info=True)
        await callback.message.edit_text("❌ Во время операции произошла непредвиденная ошибка.")


@router.message(ModerationStates.waiting_for_comment, F.text)
async def receive_moderator_comment(message: Message, state: FSMContext, db):
    """Получение комментария от модератора для отклонения или запроса изменений"""
    data = await state.get_data()
    post_id = data.get("pending_post_id")
    action = data.get("pending_action")
    comment = message.text.strip()
    
    await state.clear()

    if not all([post_id, action]):
        logfire.error("Состояние FSM не содержит всех необходимых данных (post_id или action).")
        await message.answer("❌ Состояние операции потеряно. Пожалуйста, попробуйте снова.")
        return

    logfire.info(f"Модератор {message.from_user.id} отправил комментарий для поста {post_id} с действием '{action}'.")

    try:
        post = None
        feedback_text = ""
        if action == "reject":
            post = await PostService.reject_post(db, post_id, message.from_user.id, comment)
            if post:
                await message.answer("✅ Пост отклонён. Комментарий отправлен автору.")
                feedback_text = f"❌ Ваш пост '{post.title}' отклонён.\n\nКомментарий модератора: {comment}"
        elif action == "changes":
            post = await PostService.request_changes(db, post_id, message.from_user.id, comment)
            if post:
                await message.answer("✅ Запрос на изменения отправлен автору.")
                feedback_text = f"📝 Ваш пост '{post.title}' требует изменений.\n\nКомментарий модератора: {comment}"

        if post:
            try:
                await message.bot.send_message(chat_id=post.author_id, text=feedback_text)
            except Exception as e:
                logfire.warning(f"Не удалось уведомить автора {post.author_id} о комментарии: {e}")
        else:
            logfire.error(f"Не удалось выполнить действие '{action}' для поста {post_id}.")
            await message.answer("❌ Произошла ошибка во время операции. Пост не найден или не может быть обновлен.")
            
    except Exception as e:
        logfire.error(f"Ошибка при обработке комментария модератора: {e}", exc_info=True)
        await message.answer("❌ Произошла непредвиденная ошибка при обработке комментария.")