from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_schedule_filters_kb() -> InlineKeyboardMarkup:
    """Создает клавиатуру с фильтрами времени для расписания"""
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(text="🕐 Сегодня", callback_data="schedule:today"),
        InlineKeyboardButton(text="📅 Завтра", callback_data="schedule:tomorrow"),
    )
    kb.row(
        InlineKeyboardButton(text="📊 Эта неделя", callback_data="schedule:week"),
        InlineKeyboardButton(text="🗓 Этот месяц", callback_data="schedule:month"),
    )
    kb.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"),
    )
    
    return kb.as_markup()

def get_schedule_entry_kb(booking_id: int, can_cancel: bool = True) -> InlineKeyboardMarkup:
    """Создает клавиатуру для отдельной записи в расписании"""
    kb = InlineKeyboardBuilder()
    
    if can_cancel:
        kb.row(InlineKeyboardButton(
            text="❌ Отменить занятие",
            callback_data=f"schedule:cancel:{booking_id}"
        ))
    
    kb.row(InlineKeyboardButton(
        text="🔙 Назад к расписанию",
        callback_data="schedule:back"
    ))
    
    return kb.as_markup()

def get_cancel_confirmation_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру подтверждения отмены занятия"""
    kb = InlineKeyboardBuilder()
    
    kb.row(
        InlineKeyboardButton(
            text="✅ Подтвердить отмену",
            callback_data=f"schedule:confirm_cancel:{booking_id}"
        ),
        InlineKeyboardButton(
            text="❌ Не отменять",
            callback_data="schedule:back"
        )
    )
    
    return kb.as_markup() 