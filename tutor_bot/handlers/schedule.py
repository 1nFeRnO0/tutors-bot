from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from tutor_bot.handlers.profile import back_to_main_menu

from common.database import Booking, BookingStatus, async_session_maker, Tutor, Parent
from tutor_bot.schedule_kb import (
    get_schedule_filters_kb,
    get_schedule_with_cancel_kb,
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
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from parent_bot.main import bot as parent_bot

def get_period_title(period: str, date: datetime = None) -> str:
    """Возвращает заголовок для периода"""
    if not date:
        date = datetime.now()
    
    if period == "today":
        return "сегодня"
    elif period == "tomorrow":
        return "завтра"
    elif period == "week":
        start = date - timedelta(days=date.weekday())
        end = start + timedelta(days=6)
        return f"неделю ({format_date_with_month(start.date())}-{format_date_with_month(end.date())})"
    else:  # month
        return f"месяц ({format_month_title(date.date())})"

async def show_schedule(callback_query: types.CallbackQuery):
    """Показывает расписание репетитора"""
    period = callback_query.data.split(':')[1] if ':' in callback_query.data else 'today'
    
    async with async_session_maker() as session:
        # Получаем записи для выбранного периода
        bookings = await get_bookings_for_period(
            session,
            callback_query.from_user.id,
            period
        )
        
        now = datetime.now()
        if period == "today":
            date_str = format_date_with_month(now.date())
            text = format_daily_schedule(bookings, date_str)
        elif period == "tomorrow":
            tomorrow = (now + timedelta(days=1)).date()
            date_str = format_date_with_month(tomorrow)
            text = format_daily_schedule(bookings, date_str)
        elif period == "week":
            start_date = (now - timedelta(days=now.weekday())).date()
            end_date = (start_date + timedelta(days=6))
            week_range = f"{format_date_with_month(start_date)}-{format_date_with_month(end_date)}"
            text = format_weekly_schedule(bookings, week_range)
        else:  # month
            month_str = format_month_title(now.date())
            text = format_monthly_schedule(bookings, month_str)
        
        # Отправляем сообщение с основной клавиатурой
        await callback_query.message.edit_text(
            text,
            reply_markup=get_schedule_filters_kb(bookings, period)
        )

async def handle_schedule_filter(callback: types.CallbackQuery):
    """Обработчик фильтров расписания"""
    period = callback.data.split(":")[1]
    
    async with async_session_maker() as session:
        bookings = await get_bookings_for_period(session, callback.from_user.id, period)
        
        now = datetime.now()
        if period == "today":
            date_str = format_date_with_month(now.date())
            text = format_daily_schedule(bookings, date_str)
        elif period == "tomorrow":
            tomorrow = (now + timedelta(days=1)).date()
            date_str = format_date_with_month(tomorrow)
            text = format_daily_schedule(bookings, date_str)
        elif period == "week":
            start_date = (now - timedelta(days=now.weekday())).date()
            end_date = (start_date + timedelta(days=6))
            week_range = f"{format_date_with_month(start_date)}-{format_date_with_month(end_date)}"
            text = format_weekly_schedule(bookings, week_range)
        else:  # month
            month_str = format_month_title(now.date())
            text = format_monthly_schedule(bookings, month_str)
        
        await callback.message.edit_text(
            text,
            reply_markup=get_schedule_filters_kb(bookings, period)
        )

async def handle_schedule_back(callback: types.CallbackQuery):
    """Обработчик кнопки возврата к фильтрам расписания"""
    await show_schedule(callback)

async def handle_cancel_menu(callback: types.CallbackQuery):
    """Обработчик нажатия на кнопку отмены занятий"""
    period = callback.data.split(":")[2]  # schedule:cancel:period
    
    async with async_session_maker() as session:
        # Получаем записи для выбранного периода
        bookings = await get_bookings_for_period(session, callback.from_user.id, period)
        
        # Формируем текст с занятиями для отмены
        text = [f"❌ Отмена занятий на {get_period_title(period)}\n\nВыберите занятие для отмены:\n"]
        
        now = datetime.now()
        has_bookings = False
        
        # Сортируем занятия по дате и времени
        sorted_bookings = sorted(
            bookings,
            key=lambda b: (b.date, b.start_time)
        )
        
        current_date = None
        for booking in sorted_bookings:
            booking_datetime = datetime.combine(booking.date, booking.start_time)
            
            # Добавляем разделитель даты, если она изменилась
            if period in ["week", "month"] and booking.date != current_date:
                current_date = booking.date
                text.append(f"\n📅 {format_date_with_month(current_date)}")
            
            if booking.status == BookingStatus.APPROVED:
                if period in ["today", "tomorrow"] or (period in ["week", "month"] and booking_datetime > now):
                    has_bookings = True
                    text.append(
                        f"\n⏰ {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')} | "
                        f"{booking.child.name} {booking.child.surname} ({booking.child.grade} класс) | "
                        f"{booking.subject_name}"
                    )
            elif booking.status == BookingStatus.PENDING:
                text.append(
                    f"\n⚠️ {booking.child.name} {booking.child.surname} "
                    f"({booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')}) - "
                    "ожидает подтверждения"
                )
        
        if not has_bookings:
            text.append("\nНет занятий, доступных для отмены")
        
        # Отправляем сообщение с клавиатурой отмены
        await callback.message.edit_text(
            "\n".join(text),
            reply_markup=get_schedule_with_cancel_kb(bookings, period)
        )

async def handle_cancel_booking(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку отмены конкретного занятия"""
    booking_id = int(callback.data.split(":")[2])
    
    async with async_session_maker() as session:
        # Сначала получаем id репетитора из БД
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if not tutor:
            await callback.answer("❌ Ошибка: репетитор не найден")
            return
        
        # Получаем запись с загрузкой связанных данных
        booking = await session.execute(
            select(Booking)
            .options(
                selectinload(Booking.child),
                selectinload(Booking.parent)
            )
            .where(
                Booking.id == booking_id,
                Booking.tutor_id == tutor.id,
                Booking.status == BookingStatus.APPROVED
            )
        )
        booking = booking.scalar_one_or_none()
        
        if not booking:
            await callback.answer("❌ Запись не найдена или уже была отменена")
            return
        
        # Проверяем, что до занятия больше 2 часов
        lesson_datetime = datetime.combine(booking.date, booking.start_time)
        if (lesson_datetime - datetime.now()).total_seconds() < 2 * 3600:
            await callback.answer(
                "❌ Отмена невозможна: до занятия осталось меньше 2 часов",
                show_alert=True
            )
            return
        
        # Сохраняем данные о занятии в состояние
        await state.update_data(
            booking_to_cancel={
                "id": booking.id,
                "child_name": booking.child.name,
                "child_surname": booking.child.surname,
                "subject_name": booking.subject_name,
                "date": booking.date.isoformat(),
                "start_time": booking.start_time.strftime("%H:%M"),
                "end_time": booking.end_time.strftime("%H:%M"),
                "parent_id": booking.parent_id,
                "tutor_id": tutor.id,  # Сохраняем id репетитора для последующей проверки
                "tutor_name": tutor.name,  # Сохраняем имя репетитора
                "tutor_surname": tutor.surname,  # Сохраняем фамилию репетитора
                "tutor_patronymic": tutor.patronymic  # Сохраняем отчество репетитора
            }
        )
        
        # Показываем подтверждение отмены
        text = (
            "❗️ Вы действительно хотите отменить занятие?\n\n"
            f"👤 Ребенок: {booking.child.name} {booking.child.surname}\n"
            f"📚 Предмет: {booking.subject_name}\n"
            f"📅 Дата: {format_date_with_month(booking.date)}\n"
            f"🕒 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n\n"
            "⚠️ Отмена возможна только за 2 часа до занятия"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_cancel_confirmation_kb(booking_id)
        )

async def handle_cancel_confirmation(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик подтверждения отмены занятия"""
    # Получаем сохраненные данные о занятии
    data = await state.get_data()
    booking_data = data.get("booking_to_cancel")
    
    if not booking_data:
        await callback.answer("❌ Ошибка: данные о занятии не найдены")
        return
    
    booking_id = booking_data["id"]
    
    async with async_session_maker() as session:
        # Сначала получаем id репетитора из БД для проверки
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if not tutor or tutor.id != booking_data["tutor_id"]:
            await callback.answer("❌ Ошибка: у вас нет прав на отмену этого занятия")
            return
        
        # Получаем запись без связанных данных, так как они у нас уже есть
        booking = await session.get(Booking, booking_id)
        
        if not booking or booking.status != BookingStatus.APPROVED:
            await callback.answer("❌ Запись не найдена или уже была отменена")
            return
        
        # Дополнительная проверка, что занятие принадлежит этому репетитору
        if booking.tutor_id != tutor.id:
            await callback.answer("❌ Ошибка: у вас нет прав на отмену этого занятия")
            return
        
        # Проверяем, что до занятия больше 2 часов
        lesson_datetime = datetime.combine(booking.date, booking.start_time)
        if (lesson_datetime - datetime.now()).total_seconds() < 2 * 3600:
            await callback.answer(
                "❌ Отмена невозможна: до занятия осталось меньше 2 часов",
                show_alert=True
            )
            return
        
        # Отменяем запись
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now()
        booking.cancelled_by = "tutor"
        await session.commit()
        
        # Получаем telegram_id родителя
        parent = await session.get(Parent, booking_data["parent_id"])
        if not parent:
            await callback.answer("❌ Ошибка: не удалось отправить уведомление родителю")
            return
        
        # Уведомляем родителя, используя сохраненные данные
        tutor_full_name = f"{booking_data['tutor_surname']} {booking_data['tutor_name']}"
        if booking_data['tutor_patronymic']:
            tutor_full_name += f" {booking_data['tutor_patronymic']}"
            
        notification_text = (
            "❌ Занятие отменено репетитором\n\n"
            f"👨‍🏫 Репетитор: {tutor_full_name}\n"
            f"👤 Ребенок: {booking_data['child_name']} {booking_data['child_surname']}\n"
            f"📚 Предмет: {booking_data['subject_name']}\n"
            f"📅 Дата: {format_date_with_month(datetime.fromisoformat(booking_data['date']).date())}\n"
            f"🕒 Время: {booking_data['start_time']} - {booking_data['end_time']}"
        )
        
        await parent_bot.send_message(
            chat_id=parent.telegram_id,
            text=notification_text
        )
        
        # Очищаем состояние
        await state.clear()
        
        # Возвращаемся к расписанию
        await show_schedule(callback)
        await callback.answer("✅ Занятие успешно отменено")

def register_schedule_handlers(dp):
    """Регистрирует обработчики расписания"""
    dp.callback_query.register(show_schedule, lambda c: c.data == "show_schedule")
    dp.callback_query.register(
        handle_schedule_filter,
        lambda c: c.data.startswith("schedule:") and c.data.split(":")[1] in ["today", "tomorrow", "week", "month"]
    )
    dp.callback_query.register(
        handle_cancel_menu,
        lambda c: c.data.startswith("schedule:cancel:") and c.data.split(":")[2] in ["today", "tomorrow", "week", "month"]
    )
    dp.callback_query.register(
        handle_cancel_booking,
        lambda c: c.data.startswith("schedule:cancel:") and c.data.split(":")[2].isdigit()
    )
    dp.callback_query.register(
        handle_cancel_confirmation,
        lambda c: c.data.startswith("schedule:confirm_cancel:")
    )
    dp.callback_query.register(handle_schedule_back, lambda c: c.data == "schedule:back")
    dp.callback_query.register(back_to_main_menu, lambda c: c.data == "back_to_main")