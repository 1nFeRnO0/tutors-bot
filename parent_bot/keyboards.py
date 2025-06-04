from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для начала регистрации"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Начать регистрацию", callback_data="start_registration")]
    ])

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню для зарегистрированного родителя"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="👶 Мои дети", callback_data="children")],
        [InlineKeyboardButton(text="🔍 Найти репетитора", callback_data="find_tutor")],
        [InlineKeyboardButton(text="📅 Мои записи", callback_data="my_bookings")]
    ])

def get_registration_form_keyboard(name: str = "", surname: str = "", patronymic: str = "") -> InlineKeyboardMarkup:
    """Клавиатура формы регистрации с текущими данными"""
    keyboard = [
        [
            InlineKeyboardButton(text="Имя", callback_data="edit_name"),
            InlineKeyboardButton(text=name or "Не указано", callback_data="edit_name")
        ],
        [
            InlineKeyboardButton(text="Фамилия", callback_data="edit_surname"),
            InlineKeyboardButton(text=surname or "Не указано", callback_data="edit_surname")
        ],
        [
            InlineKeyboardButton(text="Отчество", callback_data="edit_patronymic"),
            InlineKeyboardButton(text=patronymic or "Не указано", callback_data="edit_patronymic")
        ]
    ]
    
    # Добавляем кнопку "Продолжить" только если заполнены имя и фамилия
    if name and surname:
        keyboard.append([InlineKeyboardButton(text="✅ Продолжить", callback_data="finish_name_surname")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_registration_menu_keyboard(name: str = "", surname: str = "", patronymic: str = "") -> InlineKeyboardMarkup:
    """Клавиатура меню регистрации с текущими данными"""
    keyboard = [
        [
            InlineKeyboardButton(text="Имя", callback_data="edit_name"),
            InlineKeyboardButton(text=name or "Не указано", callback_data="edit_name")
        ],
        [
            InlineKeyboardButton(text="Фамилия", callback_data="edit_surname"),
            InlineKeyboardButton(text=surname or "Не указано", callback_data="edit_surname")
        ],
        [
            InlineKeyboardButton(text="Отчество", callback_data="edit_patronymic"),
            InlineKeyboardButton(text=patronymic or "Не указано", callback_data="edit_patronymic")
        ],
        [InlineKeyboardButton(text="Продолжить", callback_data="finish_registration")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 