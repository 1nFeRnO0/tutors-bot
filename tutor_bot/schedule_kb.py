from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List
from common.database import Booking, BookingStatus
from datetime import datetime, timedelta

def format_short_date(date: datetime.date) -> str:
    """Форматирует дату в короткий формат (дд.мм)"""
    return date.strftime("%d.%m")

def has_eligible_bookings(bookings: List[Booking], period: str) -> bool:
    """Проверяет, есть ли занятия, доступные для отмены"""
    now = datetime.now()
    
    for booking in bookings:
        if booking.status != BookingStatus.APPROVED:
            continue
            
        if period in ["today", "tomorrow"]:
            # Для сегодня/завтра - просто проверяем наличие подтвержденных занятий
            return True
        else:
            # Для недели/месяца - проверяем, что занятие в будущем
            booking_datetime = datetime.combine(booking.date, booking.start_time)
            if booking_datetime > now:
                return True
    
    return False

def get_schedule_filters_kb(bookings: List[Booking], current_period: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру с фильтрами расписания"""
    keyboard = [
        [
            InlineKeyboardButton(text="🕐 Сегодня", callback_data="schedule:today"),
            InlineKeyboardButton(text="📅 Завтра", callback_data="schedule:tomorrow"),
        ],
        [
            InlineKeyboardButton(text="📊 Эта неделя", callback_data="schedule:week"),
            InlineKeyboardButton(text="🗓 Этот месяц", callback_data="schedule:month"),
        ]
    ]
    
    # Добавляем кнопку отмены только если есть подходящие занятия
    if has_eligible_bookings(bookings, current_period):
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Отменить занятие",
                callback_data=f"schedule:cancel:{current_period}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_schedule_with_cancel_kb(bookings: List[Booking], period: str) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру расписания с кнопками отмены для каждого занятия"""
    keyboard = []
    now = datetime.now()
    
    # Добавляем кнопку отмены для каждого подходящего занятия
    for booking in bookings:
        if booking.status == BookingStatus.APPROVED:
            # Проверяем, подходит ли занятие под текущий фильтр
            booking_datetime = datetime.combine(booking.date, booking.start_time)
            
            if period in ["today", "tomorrow"] or (period in ["week", "month"] and booking_datetime > now):
                # Формируем текст кнопки с информацией о времени и дате
                button_text = f"❌ Отменить занятие {format_short_date(booking.date)} в {booking.start_time.strftime('%H:%M')}"
                
                keyboard.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"schedule:cancel:{booking.id}"
                    )
                ])
    
    # Добавляем кнопку возврата к фильтрам
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад к расписанию",
            callback_data="schedule:back"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_confirmation_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру подтверждения отмены занятия"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, отменить",
                    callback_data=f"schedule:confirm_cancel:{booking_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Нет, оставить",
                    callback_data="schedule:back"
                ),
            ]
        ]
    ) 