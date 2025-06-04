from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import calendar
from typing import List, Dict, Any

from common.database import Child, Tutor

def get_children_keyboard(children: List[Child]) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком детей для выбора"""
    keyboard = []
    
    for child in children:
        child_name = f"{child.name} {child.surname}"
        if child.patronymic:
            child_name = f"{child.name} {child.patronymic} {child.surname}"
        
        keyboard.append([
            InlineKeyboardButton(
                text=child_name,
                callback_data=f"book_child_{child.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="cancel_booking")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_tutors_keyboard(tutors: List[Tutor]) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком репетиторов для выбора"""
    keyboard = []
    
    for tutor in tutors:
        tutor_name = f"{tutor.name} {tutor.surname}"
        if tutor.patronymic:
            tutor_name = f"{tutor.name} {tutor.patronymic} {tutor.surname}"
        
        keyboard.append([
            InlineKeyboardButton(
                text=tutor_name,
                callback_data=f"book_tutor_{tutor.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_child_selection")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_subjects_keyboard(subjects: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Создает клавиатуру с предметами репетитора"""
    keyboard = []
    
    for subject in subjects:
        # Добавляем предмет только если доступен хотя бы один тип занятия
        if subject.get('is_standard') or subject.get('is_exam'):
            keyboard.append([
                InlineKeyboardButton(
                    text=subject['name'],
                    callback_data=f"book_subject_{subject['name']}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_tutor_selection")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_lesson_type_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с типами занятий"""
    keyboard = [
        [
            InlineKeyboardButton(text="📚 Стандартное занятие", callback_data="book_type_standard"),
            InlineKeyboardButton(text="📝 Подготовка к экзамену", callback_data="book_type_exam")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_subject_selection")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_calendar_keyboard(year: int, month: int, available_dates: List[datetime.date]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру-календарь с доступными датами
    
    Args:
        year (int): Год
        month (int): Месяц
        available_dates (List[datetime.date]): Список доступных дат
    
    Returns:
        InlineKeyboardMarkup: Клавиатура-календарь
    """
    keyboard = []
    
    # Заголовок с месяцем и годом
    month_names = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    keyboard.append([
        InlineKeyboardButton(
            text=f"📅 {month_names[month-1]} {year}",
            callback_data="ignore"
        )
    ])
    
    # Дни недели
    days_of_week = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    keyboard.append([
        InlineKeyboardButton(text=day, callback_data="ignore")
        for day in days_of_week
    ])
    
    # Получаем календарь на месяц
    cal = calendar.monthcalendar(year, month)
    
    # Добавляем дни
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                date = datetime(year, month, day).date()
                if date in available_dates:
                    row.append(InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"book_date_{date.isoformat()}"
                    ))
                else:
                    row.append(InlineKeyboardButton(text="❌", callback_data="ignore"))
        keyboard.append(row)
    
    # Кнопки навигации
    nav_row = []
    # Предыдущий месяц
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    nav_row.append(InlineKeyboardButton(
        text="◀️",
        callback_data=f"calendar_{prev_year}_{prev_month}"
    ))
    
    # Следующий месяц
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1
    nav_row.append(InlineKeyboardButton(
        text="▶️",
        callback_data=f"calendar_{next_year}_{next_month}"
    ))
    keyboard.append(nav_row)
    
    # Кнопки управления
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_lesson_type")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_time_slots_keyboard(available_slots: List[tuple]) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с доступными временными слотами
    
    Args:
        available_slots (List[tuple]): Список кортежей (время_начала, время_окончания)
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с временными слотами
    """
    keyboard = []
    
    for start_time, end_time in available_slots:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🕒 {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
                callback_data=f"book_time_{start_time.strftime('%H:%M')}_{end_time.strftime('%H:%M')}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_date_selection")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_booking_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения бронирования"""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_time_selection")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 