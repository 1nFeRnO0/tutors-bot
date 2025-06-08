from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from tutor_bot.handlers.profile import back_to_main_menu

from common.database import Booking, BookingStatus, async_session_maker
from tutor_bot.schedule_kb import (
    get_schedule_filters_kb,
    get_schedule_entry_kb,
    get_cancel_confirmation_kb
)
from tutor_bot.utils.schedule_utils import (
    get_bookings_for_period,
    format_daily_schedule,
    format_weekly_schedule,
    format_monthly_schedule,
    format_date_with_month,
    format_month_title
)

async def show_schedule(callback_query: types.CallbackQuery):
    """Показывает расписание репетитора"""
    period = 'today'  # today, tomorrow, week или month
    
    async with async_session_maker() as session:
        # Получаем записи для выбранного периода
        bookings = await get_bookings_for_period(
            session,
            callback_query.from_user.id,
            period
        )
        
        now = datetime.now()
        date_str = format_date_with_month(now.date())
        text = format_daily_schedule(bookings, date_str)
        
        # Отправляем сообщение
        await callback_query.message.edit_text(
            text,
            reply_markup=get_schedule_filters_kb()
        )

async def handle_schedule_filter(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик фильтров расписания"""
    period = callback.data.split(":")[1]
    
    async with async_session_maker() as session:
        bookings = await get_bookings_for_period(session, callback.from_user.id, period)
        print('DEBUG:bookings', bookings)
        now = datetime.now()
        if period == "today":
            date_str = format_date_with_month(now.date())
            text = format_daily_schedule(bookings, date_str)
        elif period == "tomorrow":
            tomorrow = (datetime.now() + timedelta(days=1)).date()
            date_str = format_date_with_month(tomorrow)
            text = format_daily_schedule(bookings, date_str)
        elif period == "week":
            start_date = (datetime.now() - timedelta(days=datetime.now().weekday())).date()
            end_date = (start_date + timedelta(days=6))
            week_range = f"{format_date_with_month(start_date)}-{format_date_with_month(end_date)}"
            text = format_weekly_schedule(bookings, week_range)
        elif period == "month":
            month_str = format_month_title(now.date())
            text = format_monthly_schedule(bookings, month_str)
        
        await callback.message.edit_text(
            text,
            reply_markup=get_schedule_filters_kb()
        )
        await callback.answer()

async def handle_cancel_booking(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки отмены занятия"""
    booking_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        # Получаем информацию о записи
        booking = await session.get(Booking, booking_id)
        if not booking:
            await callback.answer("❌ Запись не найдена")
            return
        
        # Проверяем, можно ли отменить запись
        if booking.status != BookingStatus.APPROVED:
            await callback.answer("❌ Можно отменять только подтвержденные занятия")
            return
        
        # Формируем сообщение подтверждения
        text = (
            "⚠️ Подтверждение отмены\n\n"
            f"Вы собираетесь отменить:\n"
            f"⏰ {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}, "
            f"{booking.date.strftime('%d.%m.%Y')}\n"
            f"👤 {booking.child.name} {booking.child.surname} ({booking.child.grade} класс)\n"
            f"📚 {booking.subject_name} ({booking.lesson_type})\n\n"
            "Укажите причину отмены в следующем сообщении:"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_cancel_confirmation_kb(booking_id)
        )
        await callback.answer()

async def handle_confirm_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик подтверждения отмены занятия"""
    booking_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        # Получаем информацию о записи
        booking = await session.get(Booking, booking_id)
        if not booking:
            await callback.answer("❌ Запись не найдена")
            return
        
        # Отмечаем запись как отмененную
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.utcnow()
        await session.commit()
        
        # Возвращаемся к расписанию
        bookings = await get_bookings_for_period(session, callback.from_user.id, "today")
        today_str = datetime.now().strftime("%d.%m.%Y")
        
        await callback.message.edit_text(
            format_daily_schedule(bookings, today_str),
            reply_markup=get_schedule_filters_kb()
        )
        await callback.answer("✅ Занятие успешно отменено")

async def handle_schedule_back(callback: types.CallbackQuery):
    """Обработчик возврата к расписанию"""
    async with async_session_maker() as session:
        bookings = await get_bookings_for_period(session, callback.from_user.id, "today")
        today_str = datetime.now().strftime("%d.%m.%Y")
        
        await callback.message.edit_text(
            format_daily_schedule(bookings, today_str),
            reply_markup=get_schedule_filters_kb()
        )
        await callback.answer()

def register_schedule_handlers(dp):
    """Регистрация обработчиков расписания"""
    dp.callback_query.register(show_schedule, lambda c: c.data == "show_schedule")
    dp.callback_query.register(handle_schedule_filter, lambda c: c.data.startswith("schedule:") and not c.data.startswith("schedule:cancel"))
    dp.callback_query.register(handle_cancel_booking, lambda c: c.data.startswith("schedule:cancel:"))
    dp.callback_query.register(handle_confirm_cancel, lambda c: c.data.startswith("schedule:confirm_cancel:"))
    dp.callback_query.register(handle_schedule_back, lambda c: c.data == "schedule:back")
    dp.callback_query.register(back_to_main_menu, lambda c: c.data == "back_to_main")