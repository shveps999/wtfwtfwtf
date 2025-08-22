from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest # --- ИСПРАВЛЕНИЕ: Добавлен импорт TelegramBadRequest ---
import logfire # --- ИСПРАВЛЕНИЕ: logfire уже был импортирован, но теперь будет использоваться ---

from events_bot.database.services import UserService, CategoryService, LikeService, NotificationService
from events_bot.bot.states import UserStates
from events_bot.bot.keyboards import get_category_selection_keyboard, get_main_keyboard


router = Router()


def register_callback_handlers(dp: Router):
    """Регистрация обработчиков callback"""
    dp.include_router(router)


@router.callback_query(F.data.startswith("category_"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext, db):
    """Обработка выбора категории (множественный выбор)"""
    user_id = callback.from_user.id
    logfire.info(f"Пользователь {user_id} выбирает категорию: {callback.data}")
    
    try:
        # --- ИСПРАВЛЕНИЕ: Безопасное извлечение category_id ---
        parts = callback.data.split("_")
        if len(parts) < 2 or not parts[1].isdigit():
            logfire.error(f"Неверный формат callback-данных категории: {callback.data}")
            await callback.answer("❌ Неверные данные категории.", show_alert=True)
            return
        category_id = int(parts[1])

        # Получаем все категории
        categories = await CategoryService.get_all_categories(db)
        if not categories:
            logfire.error("Не удалось загрузить категории из базы данных.")
            await callback.answer("❌ Не удалось загрузить категории. Попробуйте позже.", show_alert=True)
            return

        # Получаем текущие выбранные категории
        data = await state.get_data()
        selected_ids = data.get("selected_categories", [])

        # Добавляем или удаляем категорию из выбранных
        if category_id in selected_ids:
            selected_ids.remove(category_id)
            logfire.info(f"Категория {category_id} удалена из выбора для пользователя {user_id}.")
        else:
            selected_ids.append(category_id)
            logfire.info(f"Категория {category_id} добавлена в выбор для пользователя {user_id}.")

        await state.update_data(selected_categories=selected_ids)

        # Обновляем клавиатуру
        await callback.message.edit_reply_markup(
            reply_markup=get_category_selection_keyboard(categories, selected_ids)
        )
    except TelegramBadRequest:
        logfire.warning(f"TelegramBadRequest при обновлении клавиатуры для {user_id}. Вероятно, клавиатура не изменилась.")
        # Не нужно отвечать, если ошибка была из-за неизменности.
    except Exception as e:
        logfire.error(f"Ошибка при обработке выбора категории для пользователя {user_id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при выборе категории.", show_alert=True)
    finally:
        await callback.answer() # Отвечаем на callback, если еще не ответили


@router.callback_query(F.data == "confirm_categories")
async def confirm_categories_selection(callback: CallbackQuery, state: FSMContext, db):
    """Подтверждение выбора категорий"""
    user_id = callback.from_user.id
    logfire.info(f"Пользователь {user_id} подтверждает выбор категорий.")
    
    try:
        data = await state.get_data()
        selected_ids = data.get("selected_categories", [])

        if not selected_ids:
            await callback.answer("❌ Пожалуйста, выберите хотя бы одну категорию!", show_alert=True)
            return

        # Сохраняем выбранные категории пользователю
        await UserService.select_categories(db, user_id, selected_ids)
        logfire.info(f"Пользователь {user_id} выбрал категории: {selected_ids}.")

        # Получаем названия выбранных категорий
        categories = await CategoryService.get_all_categories(db)
        selected_category_names = [cat.name for cat in categories if cat.id in selected_ids]
        category_names_str = ", ".join(selected_category_names)

        # --- ИСПРАВЛЕНИЕ: Редактируем сообщение один раз, чтобы избежать TelegramBadRequest ---
        await callback.message.edit_text(
            f"✅ Ваши выбранные категории: {category_names_str}\n\n"
            "Теперь вы будете получать уведомления о новых постах в этих категориях.",
            reply_markup=get_main_keyboard() # Устанавливаем основную клавиатуру сразу
        )
        await state.clear()
        await callback.answer("✅ Категории успешно сохранены!")
        
    except TelegramBadRequest:
        logfire.warning(f"TelegramBadRequest при подтверждении категорий для {user_id}. Возможно, сообщение уже изменилось.")
        await callback.answer("ℹ️ Сообщение уже актуально.")
    except Exception as e:
        logfire.error(f"Ошибка при подтверждении категорий для пользователя {user_id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при сохранении категорий.", show_alert=True)


@router.callback_query(F.data.startswith("like_post_"))
async def handle_like_from_notification(callback: CallbackQuery, db):
    """Обработка лайка из уведомления"""
    user_id = callback.from_user.id
    logfire.info(f"Пользователь {user_id} нажал кнопку 'лайк' для поста: {callback.data}")
    
    try:
        # --- ИСПРАВЛЕНИЕ: Безопасное извлечение post_id ---
        parts = callback.data.split("_")
        if len(parts) < 3 or not parts[2].isdigit():
            logfire.error(f"Неверный формат callback-данных лайка: {callback.data}")
            await callback.answer("❌ Неверные данные для лайка.", show_alert=True)
            return
        post_id = int(parts[2])

        # Переключаем лайк
        # --- ИСПРАВЛЕНИЕ: LikeService.toggle_like должен возвращать четкий статус (liked/unliked) ---
        result = await LikeService.toggle_like(db, user_id, post_id)
        
        # Предполагаем, что result['action'] возвращает 'added' или 'removed'
        is_liked = (result and result.get("action") == "added") # Проверяем наличие ключа 'action'
        action_text = "добавлен в избранное ❤️" if is_liked else "удален из избранного ✅"

        await callback.answer(f"Пост {action_text}", show_alert=False) # show_alert=False для менее навязчивых уведомлений

        # Обновляем клавиатуру
        new_keyboard = NotificationService.get_like_keyboard(post_id, is_liked)
        await callback.message.edit_reply_markup(reply_markup=new_keyboard)

    except TelegramBadRequest:
        logfire.warning(f"TelegramBadRequest при обновлении кнопки лайка для пользователя {user_id}. Состояние уже актуально.")
        # Можно ответить, чтобы пользователь видел, что действие обработано, но не всплывающим окном.
        await callback.answer("ℹ️ Состояние уже актуально.")
    except Exception as e:
        logfire.error(f"Ошибка при обработке лайка для пользователя {user_id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при добавлении/удалении из избранного.", show_alert=True)