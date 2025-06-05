from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from common.database import Child, Gender

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
        [InlineKeyboardButton(text="🔍 Мои репетиторы", callback_data="tutors")],
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

def get_children_list_keyboard(children: list[Child]) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком детей и кнопками управления"""
    keyboard = []
    
    for child in children:
        # Формируем ФИО ребенка
        child_name = f"{child.name} {child.surname}"
        if child.patronymic:
            child_name = f"{child.name} {child.patronymic} {child.surname}"
            
        # Добавляем строку с именем и кнопками управления
        keyboard.append([
            InlineKeyboardButton(text=child_name, callback_data=f"child_info_{child.id}"),
            InlineKeyboardButton(text="✏️", callback_data=f"edit_child_{child.id}"),
            InlineKeyboardButton(text="❌", callback_data=f"delete_child_{child.id}")
        ])
    
    # Добавляем кнопку добавления нового ребенка
    keyboard.append([InlineKeyboardButton(text="➕ Добавить ребенка", callback_data="add_child")])
    
    # Добавляем кнопку возврата в главное меню
    keyboard.append([InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_gender_keyboard(selected_gender: Gender = None, is_edit: bool = False) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора пола"""
    prefix = "edit_gender" if is_edit else "add_gender"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{'✓ ' if selected_gender == Gender.MALE else ''}М", 
                callback_data=f"{prefix}_M"
            ),
            InlineKeyboardButton(
                text=f"{'✓ ' if selected_gender == Gender.FEMALE else ''}Ж", 
                callback_data=f"{prefix}_F"
            )
        ]
    ])

def get_grade_keyboard(selected_grade: int = None, is_edit: bool = False) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора класса"""
    prefix = "edit_grade" if is_edit else "add_grade"
    keyboard = []
    row = []
    for grade in range(1, 12):
        row.append(InlineKeyboardButton(
            text=f"{'✓ ' if grade == selected_grade else ''}{grade}",
            callback_data=f"{prefix}_{grade}"
        ))
        if len(row) == 4:  # По 4 кнопки в ряду
            keyboard.append(row)
            row = []
    if row:  # Добавляем оставшиеся кнопки
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_child_edit_keyboard(child: Child) -> InlineKeyboardMarkup:
    """Создает клавиатуру для редактирования данных ребенка"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ФИО", callback_data="edit_fio")],
        [
            InlineKeyboardButton(text="Класс", callback_data="edit_grade"),
            InlineKeyboardButton(text=str(child.grade), callback_data="edit_grade")
        ],
        [InlineKeyboardButton(text="📚 Изменить учебник", callback_data="edit_textbook")],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="show_children")]
    ])

def get_fio_edit_keyboard(child: Child) -> InlineKeyboardMarkup:
    """Создает клавиатуру для редактирования ФИО"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Имя", callback_data="child_edit_name"),
            InlineKeyboardButton(text=child.name or "Не указано", callback_data="child_edit_name")
        ],
        [
            InlineKeyboardButton(text="Фамилия", callback_data="child_edit_surname"),
            InlineKeyboardButton(text=child.surname or "Не указано", callback_data="child_edit_surname")
        ],
        [
            InlineKeyboardButton(text="Отчество", callback_data="child_edit_patronymic"),
            InlineKeyboardButton(text=child.patronymic or "Не указано", callback_data="child_edit_patronymic")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="edit_back")]
    ])

def get_tutors_list_keyboard(tutors: list) -> InlineKeyboardMarkup:
    """Создает клавиатуру со списком репетиторов и кнопками управления"""
    keyboard = []
    
    for tutor in tutors:
        # Формируем ФИО репетитора
        tutor_name = f"{tutor.name} {tutor.surname}"
        if tutor.patronymic:
            tutor_name = f"{tutor.name} {tutor.patronymic} {tutor.surname}"
            
        # Добавляем строку с именем и кнопкой удаления
        keyboard.append([
            InlineKeyboardButton(text=tutor_name, callback_data=f"favorite_tutor_info_{tutor.id}"),
            InlineKeyboardButton(text="❌", callback_data=f"favorite_delete_tutor_{tutor.id}")
        ])
    
    # Добавляем кнопку добавления нового репетитора
    keyboard.append([InlineKeyboardButton(text="➕ Добавить репетитора", callback_data="add_tutor")])
    
    # Добавляем кнопку возврата в главное меню
    keyboard.append([InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_confirm_delete_tutor_keyboard(tutor_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения удаления репетитора"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data=f"favorite_confirm_delete_tutor_{tutor_id}"),
            InlineKeyboardButton(text="Нет", callback_data="tutors")
        ]
    ]) 