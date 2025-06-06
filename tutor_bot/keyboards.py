from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DAY_NAMES = {
    'monday': 'Пн',
    'tuesday': 'Вт',
    'wednesday': 'Ср',
    'thursday': 'Чт',
    'friday': 'Пт',
    'saturday': 'Сб',
    'sunday': 'Вс'
}

SUBJECTS = [
    "Математика",
    "Физика",
    "Химия",
    "Биология",
    "Русский язык",
    "Литература",
    "История",
    "Обществознание",
    "Английский язык",
    "Информатика"
]

def get_start_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать регистрацию", callback_data="start_registration")]
    ])
    return keyboard

def get_subjects_keyboard(selected_subjects: list) -> InlineKeyboardMarkup:
    """
    selected_subjects: [{"name": "Математика", "is_exam": True, "is_standard": True}, ...]
    """
    keyboard = []
    for subject in SUBJECTS:
        # Находим предмет в выбранных
        subject_data = next(
            (s for s in selected_subjects if s["name"] == subject),
            {"name": subject, "is_exam": False, "is_standard": False}
        )
        
        # Создаем строку с тремя кнопками для каждого предмета
        row = [
            InlineKeyboardButton(
                text=f"{subject}",
                callback_data=f"subject_name_{subject}"  # Неактивная кнопка с названием
            ),
            InlineKeyboardButton(
                text=f"{'✅' if subject_data['is_exam'] else '⬜'} ОГЭ/ЕГЭ",
                callback_data=f"subject_{subject}_exam"
            ),
            InlineKeyboardButton(
                text=f"{'✅' if subject_data['is_standard'] else '⬜'} Стандарт",
                callback_data=f"subject_{subject}_standard"
            )
        ]
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(text="💾 Сохранить", callback_data="registration_finish_subjects")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_schedule_table(schedule: dict) -> InlineKeyboardMarkup:
    keyboard = []
    for day_code, day_name in DAY_NAMES.items():
        day_info = schedule.get(day_code, {"active": False, "start": "", "end": ""})
        status = "✅" if day_info["active"] else "⬜"
        row = [
            InlineKeyboardButton(
                text=f"{status} {day_name}",
                callback_data=f"toggle_{day_code}"
            )
        ]
        if day_info["active"]:
            row.extend([
                InlineKeyboardButton(
                    text=f"🕒 {day_info['start'] or '--:--'}",
                    callback_data=f"set_start_{day_code}"
                ),
                InlineKeyboardButton(
                    text=f"🕕 {day_info['end'] or '--:--'}",
                    callback_data=f"set_end_{day_code}"
                )
            ])
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="Сохранить расписание", callback_data="save_schedule")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_hour_keyboard(day_code: str, time_type: str) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for hour in range(24):
        if len(row) == 4:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(
            text=f"{hour:02d}",
            callback_data=f"set_{time_type}_hour_{day_code}_{hour:02d}"
        ))
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="back_to_schedule")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_minute_keyboard(day_code: str, time_type: str, hour: int) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for minute in range(0, 60, 5):
        if len(row) == 4:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(
            text=f"{minute:02d}",
            callback_data=f"set_{time_type}_minute_{day_code}_{hour}_{minute}"
        ))
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="back_to_schedule")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_registration_form_keyboard(name: str = "", surname: str = "", patronymic: str = "") -> InlineKeyboardMarkup:
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

    if name and surname:
        keyboard.append([InlineKeyboardButton(text="✅ Продолжить", callback_data="finish_name_surname")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="👤 Изменить имя и фамилию", callback_data="edit_profile_name")],
        [InlineKeyboardButton(text="📚 Изменить предметы", callback_data="edit_profile_subjects")],
        [InlineKeyboardButton(text="💰 Изменить цены", callback_data="edit_profile_prices")],
        [InlineKeyboardButton(text="📝 Изменить описание", callback_data="edit_profile_description")],
        [InlineKeyboardButton(text="🕒 Изменить расписание", callback_data="edit_profile_schedule")],
        [InlineKeyboardButton(text="◀️ Вернуться в главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="📋 Ожидающие записи", callback_data="tutor_pending_bookings")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton(text="📝 Редактировать профиль", callback_data="edit_profile")],
        [InlineKeyboardButton(text="📅 Моё расписание", callback_data="schedule")],
        [InlineKeyboardButton(text="📊 Мои ученики", callback_data="my_students")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_edit_keyboard(name: str = "", surname: str = "", patronymic: str = "") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="👤 Изменить имя", callback_data="profile_edit_name"),
            InlineKeyboardButton(text=name or "❌ Не указано", callback_data="profile_edit_name")
        ],
        [
            InlineKeyboardButton(text="👤 Изменить фамилию", callback_data="profile_edit_surname"),
            InlineKeyboardButton(text=surname or "❌ Не указано", callback_data="profile_edit_surname")
        ],
        [
            InlineKeyboardButton(text="👤 Изменить отчество", callback_data="profile_edit_patronymic"),
            InlineKeyboardButton(text=patronymic or "❌ Не указано", callback_data="profile_edit_patronymic")
        ],
        [InlineKeyboardButton(text="💾 Сохранить изменения", callback_data="profile_save_name_surname")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_subjects_keyboard(selected_subjects: list) -> InlineKeyboardMarkup:
    """
    selected_subjects: [{"name": "Математика", "is_exam": True, "is_standard": True}, ...]
    """
    keyboard = []
    for subject in SUBJECTS:
        # Находим предмет в выбранных
        subject_data = next(
            (s for s in selected_subjects if s["name"] == subject),
            {"name": subject, "is_exam": False, "is_standard": False}
        )
        
        # Создаем строку с тремя кнопками для каждого предмета
        row = [
            InlineKeyboardButton(
                text=f"{subject}",
                callback_data=f"subject_name_{subject}"  # Неактивная кнопка с названием
            ),
            InlineKeyboardButton(
                text=f"{'✅' if subject_data['is_exam'] else '⬜'} ОГЭ/ЕГЭ",
                callback_data=f"profile_subject_{subject}_exam"
            ),
            InlineKeyboardButton(
                text=f"{'✅' if subject_data['is_standard'] else '⬜'} Стандарт",
                callback_data=f"profile_subject_{subject}_standard"
            )
        ]
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton(text="Сохранить", callback_data="profile_save_subjects")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_description_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="profile_cancel_description")],
        [InlineKeyboardButton(text="💾 Сохранить описание", callback_data="profile_save_description")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_schedule_keyboard(schedule: dict) -> InlineKeyboardMarkup:
    keyboard = []
    for day_code, day_name in DAY_NAMES.items():
        day_info = schedule.get(day_code, {"active": False, "start": "", "end": ""})
        status = "✅" if day_info["active"] else "⬜"
        row = [
            InlineKeyboardButton(
                text=f"{status} {day_name}",
                callback_data=f"profile_toggle_{day_code}"
            )
        ]
        if day_info["active"]:
            row.extend([
                InlineKeyboardButton(
                    text=f"🕒 {day_info['start'] or '--:--'}",
                    callback_data=f"profile_set_start_{day_code}"
                ),
                InlineKeyboardButton(
                    text=f"🕕 {day_info['end'] or '--:--'}",
                    callback_data=f"profile_set_end_{day_code}"
                )
            ])
        keyboard.append(row)
    keyboard.append([
        InlineKeyboardButton(text="◀️ Отмена", callback_data="profile_cancel_schedule"),
        InlineKeyboardButton(text="💾 Сохранить расписание", callback_data="profile_save_schedule")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_hour_keyboard(day_code: str, time_type: str) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for hour in range(24):
        if len(row) == 4:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(
            text=f"{hour:02d}",
            callback_data=f"profile_hour_{time_type}_{day_code}_{hour}"
        ))
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="profile_cancel_time")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_minute_keyboard(day_code: str, time_type: str, hour: int) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for minute in range(0, 60, 5):
        if len(row) == 4:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(
            text=f"{minute:02d}",
            callback_data=f"profile_minute_{time_type}_{day_code}_{hour}_{minute}"
        ))
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="profile_cancel_time")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_prices_keyboard(subjects: list) -> InlineKeyboardMarkup:
    """
    subjects: [{"name": "Математика", "is_exam": True, "is_standard": True, "exam_price": 2000, "standard_price": 1500}, ...]
    """
    keyboard = []
    
    # Заголовок таблицы
    keyboard.append([
        InlineKeyboardButton(text="📚 Предмет", callback_data="price_header"),
        InlineKeyboardButton(text="📖 ОГЭ/ЕГЭ", callback_data="price_header"),
        InlineKeyboardButton(text="📚 Стандарт", callback_data="price_header")
    ])
    
    # Разделитель
    keyboard.append([
        InlineKeyboardButton(text="─────────────", callback_data="price_header"),
        InlineKeyboardButton(text="─────────────", callback_data="price_header"),
        InlineKeyboardButton(text="─────────────", callback_data="price_header")
    ])
    
    # Строки с предметами и ценами
    for subject_data in subjects:
        subject = subject_data["name"]
        exam_price = subject_data.get("exam_price", 0) if subject_data["is_exam"] else "—"
        standard_price = subject_data.get("standard_price", 0) if subject_data["is_standard"] else "—"
        
        row = [
            InlineKeyboardButton(
                text=f"{subject}",
                callback_data=f"price_subject_{subject}"
            ),
            InlineKeyboardButton(
                text=f"{exam_price}₽" if isinstance(exam_price, int) else exam_price,
                callback_data=f"price_edit_{subject}_exam" if subject_data["is_exam"] else "price_header"
            ),
            InlineKeyboardButton(
                text=f"{standard_price}₽" if isinstance(standard_price, int) else standard_price,
                callback_data=f"price_edit_{subject}_standard" if subject_data["is_standard"] else "price_header"
            )
        ]
        keyboard.append(row)
    
    # Кнопки управления
    keyboard.append([
        InlineKeyboardButton(text="💾 Сохранить цены", callback_data="price_save"),
        InlineKeyboardButton(text="◀️ Отмена", callback_data="price_cancel")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_registration_prices_keyboard(subjects: list) -> InlineKeyboardMarkup:
    """
    subjects: [{"name": "Математика", "is_exam": True, "is_standard": True, "exam_price": 2000, "standard_price": 1500}, ...]
    """
    keyboard = []
    
    # Заголовок таблицы
    keyboard.append([
        InlineKeyboardButton(text="📚 Предмет", callback_data="price_header"),
        InlineKeyboardButton(text="📖 ОГЭ/ЕГЭ", callback_data="price_header"),
        InlineKeyboardButton(text="📚 Стандарт", callback_data="price_header")
    ])
    
    # Разделитель
    keyboard.append([
        InlineKeyboardButton(text="─────────────", callback_data="price_header"),
        InlineKeyboardButton(text="─────────────", callback_data="price_header"),
        InlineKeyboardButton(text="─────────────", callback_data="price_header")
    ])
    
    # Строки с предметами и ценами
    for subject_data in subjects:
        subject = subject_data["name"]
        exam_price = subject_data.get("exam_price", 0) if subject_data["is_exam"] else "—"
        standard_price = subject_data.get("standard_price", 0) if subject_data["is_standard"] else "—"
        
        row = [
            InlineKeyboardButton(
                text=f"{subject}",
                callback_data=f"registration_price_subject_{subject}"
            ),
            InlineKeyboardButton(
                text=f"{exam_price}₽" if isinstance(exam_price, int) else exam_price,
                callback_data=f"registration_price_edit_{subject}_exam" if subject_data["is_exam"] else "price_header"
            ),
            InlineKeyboardButton(
                text=f"{standard_price}₽" if isinstance(standard_price, int) else standard_price,
                callback_data=f"registration_price_edit_{subject}_standard" if subject_data["is_standard"] else "price_header"
            )
        ]
        keyboard.append(row)
    
    # Кнопки управления
    keyboard.append([
        InlineKeyboardButton(text="💾 Сохранить цены", callback_data="registration_price_save"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="registration_price_back")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_registration_description_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="◀️ Назад", callback_data="registration_description_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)