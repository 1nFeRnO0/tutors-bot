from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from common.database import async_session_maker, Booking, BookingStatus
from common.config import TUTOR_BOT_TOKEN, PARENT_BOT_TOKEN

tutor_bot = Bot(token=TUTOR_BOT_TOKEN)
parent_bot = Bot(token=PARENT_BOT_TOKEN)

async def format_lesson_notification(booking: Booking, hours_left: float, is_tutor: bool = False) -> tuple[str, InlineKeyboardMarkup]:
    """Форматирует уведомление о предстоящем занятии"""
    hours_text = "час" if 0.9 < hours_left < 1.1 else "часа" if 1 < hours_left < 5 else "часов"

    if is_tutor:
        text = (
            f"🔔 Напоминание о предстоящем занятии через {int(hours_left)} {hours_text}!\n\n"
            f"👤 Ученик: {booking.child.name} {booking.child.surname}\n"
            f"📚 Предмет: {booking.subject_name} ({'Подготовка к экзамену' if booking.lesson_type == 'exam' else 'Стандартное занятие'})\n"
            f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
            f"💰 Стоимость: {booking.price} ₽\n\n"
            f"📱 Контакт родителя: {booking.parent.phone if booking.parent.phone else 'Не указан'}"
        )
    else:
        text = (
            f"🔔 Напоминание о предстоящем занятии через {int(hours_left)} {hours_text}!\n\n"
            f"👤 Ученик: {booking.child.name} {booking.child.surname}\n"
            f"👨‍🏫 Репетитор: {booking.tutor.name} {booking.tutor.surname}\n"
            f"📚 Предмет: {booking.subject_name} ({'Подготовка к экзамену' if booking.lesson_type == 'exam' else 'Стандартное занятие'})\n"
            f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
            f"💰 Стоимость: {booking.price} ₽"
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Показать все записи", callback_data="my_bookings" if not is_tutor else "tutor_pending_bookings")]
    ])

    return text, keyboard

async def check_and_send_notifications():
    """Проверяет предстоящие занятия и отправляет уведомления"""
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    async with async_session_maker() as session:
        # Получаем все подтвержденные записи на сегодня и завтра
        upcoming_bookings = await session.execute(
            select(Booking)
            .options(
                selectinload(Booking.tutor),
                selectinload(Booking.parent),
                selectinload(Booking.child)
            )
            .where(
                and_(
                    Booking.status == BookingStatus.APPROVED,
                    Booking.date.in_([today, tomorrow])
                )
            )
        )
        upcoming_bookings = upcoming_bookings.scalars().all()

        for booking in upcoming_bookings:
            lesson_datetime = datetime.combine(booking.date, booking.start_time)
            time_to_lesson = lesson_datetime - now
            hours_to_lesson = time_to_lesson.total_seconds() / 3600

            # Проверяем, нужно ли отправлять уведомление за 24 часа
            if 23.5 <= hours_to_lesson <= 24.5 and not booking.notification_24h_sent:
                # Отправляем уведомление репетитору
                text, keyboard = await format_lesson_notification(booking, hours_to_lesson, is_tutor=True)
                try:
                    await tutor_bot.send_message(
                        chat_id=booking.tutor.telegram_id,
                        text=text,
                        reply_markup=keyboard
                    )
                except Exception as e:
                    print(f"Error sending notification to tutor: {e}")

                # Отправляем уведомление родителю
                text, keyboard = await format_lesson_notification(booking, hours_to_lesson, is_tutor=False)
                try:
                    await parent_bot.send_message(
                        chat_id=booking.parent.telegram_id,
                        text=text,
                        reply_markup=keyboard
                    )
                except Exception as e:
                    print(f"Error sending notification to parent: {e}")

                # Отмечаем, что уведомление за 24 часа отправлено
                booking.notification_24h_sent = True
                await session.commit()

            # Проверяем, нужно ли отправлять уведомление за 1 час
            elif 0.9 <= hours_to_lesson <= 1.1 and not booking.notification_1h_sent:
                # Отправляем уведомление репетитору
                text, keyboard = await format_lesson_notification(booking, hours_to_lesson, is_tutor=True)
                try:
                    await tutor_bot.send_message(
                        chat_id=booking.tutor.telegram_id,
                        text=text,
                        reply_markup=keyboard
                    )
                except Exception as e:
                    print(f"Error sending notification to tutor: {e}")

                # Отправляем уведомление родителю
                text, keyboard = await format_lesson_notification(booking, hours_to_lesson, is_tutor=False)
                try:
                    await parent_bot.send_message(
                        chat_id=booking.parent.telegram_id,
                        text=text,
                        reply_markup=keyboard
                    )
                except Exception as e:
                    print(f"Error sending notification to parent: {e}")

                # Отмечаем, что уведомление за 1 час отправлено
                booking.notification_1h_sent = True
                await session.commit() 

            # Проверяем, нужно ли отправлять уведомление меньше чем за 1 час
            elif 0.05 <= hours_to_lesson <= 1.1 and not booking.notification_1h_sent:
                print(hours_to_lesson)
                # Отправляем уведомление репетитору
                text, keyboard = await format_lesson_notification(booking, hours_to_lesson, is_tutor=True)
                try:
                    await tutor_bot.send_message(
                        chat_id=booking.tutor.telegram_id,
                        text=text,
                        reply_markup=keyboard
                    )
                except Exception as e:
                    print(f"Error sending notification to tutor: {e}")

                # Отправляем уведомление родителю
                text, keyboard = await format_lesson_notification(booking, hours_to_lesson, is_tutor=False)
                try:
                    await parent_bot.send_message(
                        chat_id=booking.parent.telegram_id,
                        text=text,
                        reply_markup=keyboard
                    )
                except Exception as e:
                    print(f"Error sending notification to parent: {e}")

                # Отмечаем, что уведомление за 1 час отправлено
                booking.notification_1h_sent = True
                await session.commit() 