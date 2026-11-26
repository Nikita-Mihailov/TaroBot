import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except Exception as e:
            # Логируем ошибку, чтобы вы могли её увидеть в консоли
            logging.error(f"Ошибка при обработке {event}: {e}", exc_info=True)

            # Пытаемся ответить пользователю, чтобы он не остался в неведении
            try:
                if isinstance(event, Message):
                    await event.answer("Упс! Что-то пошло не так. Попробуйте позже.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Произошла ошибка. Попробуйте еще раз.", show_alert=True)
            except Exception:
                pass  # Если не удалось ответить (например, бот заблокирован), просто игнорируем