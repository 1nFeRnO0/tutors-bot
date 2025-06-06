from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from common.database import Tutor, get_session
from tutor_bot.keyboards import (
    get_main_menu_keyboard,
    get_profile_menu_keyboard,
    get_profile_edit_keyboard,
    get_profile_subjects_keyboard,
    get_profile_description_keyboard,
    get_profile_schedule_keyboard,
    get_profile_hour_keyboard,
    get_profile_minute_keyboard,
    DAY_NAMES,
    get_profile_prices_keyboard
)

class ProfileEditing(StatesGroup):
    editing_name = State()
    editing_surname = State()
    editing_patronymic = State()
    editing_subjects = State()
    editing_prices = State()
    waiting_for_price_input = State()
    editing_description = State()
    editing_schedule = State()

async def show_profile(callback_query: types.CallbackQuery):
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if not tutor:
            await callback_query.answer("❌ Профиль не найден!")
            return
        
        # Форматируем список предметов с типами и ценами
        subjects_text = []
        for subject in tutor.subjects:
            types = []
            if subject["is_exam"]:
                price = subject.get("exam_price", 0)
                types.append(f"📚 ОГЭ/ЕГЭ: {price}₽/час")
            if subject["is_standard"]:
                price = subject.get("standard_price", 0)
                types.append(f"📖 Стандарт: {price}₽/час")
            subjects_text.append(f"• {subject['name']}\n  {'\n  '.join(types)}")
        
        # Формируем полное имя с отчеством (если есть)
        full_name = f"{tutor.name} {tutor.surname}"
        if tutor.patronymic:
            full_name = f"{tutor.name} {tutor.patronymic} {tutor.surname}"
        
        profile_text = (
            f"👤 <b>Профиль репетитора</b>\n\n"
            f"👤 Telegram ID: {tutor.telegram_id}\n\n"
            f"👤 Имя: {full_name}\n\n"
            f"📚 <b>Предметы и цены:</b>\n{chr(10).join(subjects_text)}\n\n"
            f"📝 <b>О себе:</b>\n{tutor.description}\n\n"
            f"🕒 <b>Расписание:</b>\n"
        )
        
        # Добавляем информацию о расписании
        for day_code, day_name in DAY_NAMES.items():
            day_info = tutor.schedule.get(day_code, {})
            if day_info.get("active"):
                profile_text += f"📅 {day_name}: {day_info['start']} - {day_info['end']}\n"
        
        await callback_query.message.edit_text(
            profile_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )

async def show_edit_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "📝 Выберите, что хотите изменить:",
        reply_markup=get_profile_menu_keyboard()
    )

async def back_to_main_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard()
    )

async def edit_profile_name(callback_query: types.CallbackQuery, state: FSMContext):
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            await state.update_data(
                name=tutor.name,
                surname=tutor.surname,
                patronymic=tutor.patronymic
            )
            await callback_query.message.edit_text(
                "Редактирование профиля:",
                reply_markup=get_profile_edit_keyboard(
                    name=tutor.name,
                    surname=tutor.surname,
                    patronymic=tutor.patronymic
                )
            )
            await state.set_state(ProfileEditing.editing_name)

async def process_edit_name(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    await callback_query.message.edit_text(
        "Введите новое имя:"
    )
    await state.set_state(ProfileEditing.editing_name)

async def process_edit_surname(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    await callback_query.message.edit_text(
        "Введите новую фамилию:"
    )
    await state.set_state(ProfileEditing.editing_surname)

async def process_edit_patronymic(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    await callback_query.message.edit_text(
        "Введите новое отчество (или оставьте пустым):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="profile_cancel_patronymic")]
        ])
    )
    await state.set_state(ProfileEditing.editing_patronymic)

async def process_name_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    data = await state.get_data()
    await state.update_data(name=message.text)
    await message.answer(
        "Редактирование профиля:",
        reply_markup=get_profile_edit_keyboard(name=message.text, surname=data.get("surname", ""), patronymic=data.get("patronymic", ""))
    )
    print(message.text)
    await state.set_state(ProfileEditing.editing_name)

async def process_surname_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_surname.state:
        return
        
    data = await state.get_data()
    await state.update_data(surname=message.text)
    await message.answer(
        "Редактирование профиля:",
        reply_markup=get_profile_edit_keyboard(name=data.get("name", ""), surname=message.text, patronymic=data.get("patronymic", ""))
    )
    await state.set_state(ProfileEditing.editing_name)

async def process_patronymic_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_patronymic.state:
        return
        
    data = await state.get_data()
    await state.update_data(patronymic=message.text)
    await message.answer(
        "Редактирование профиля:",
        reply_markup=get_profile_edit_keyboard(
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            patronymic=message.text
        )
    )
    await state.set_state(ProfileEditing.editing_name)

async def cancel_patronymic_edit(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback_query.message.edit_text(
        "Редактирование профиля:",
        reply_markup=get_profile_edit_keyboard(
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            patronymic=data.get("patronymic", "")
        )
    )
    await state.set_state(ProfileEditing.editing_name)

async def save_profile_name_surname(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_name.state:
        return
        
    data = await state.get_data()
    if not data.get("name") or not data.get("surname"):
        await callback_query.answer("Пожалуйста, заполните имя и фамилию!")
        return
    
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            tutor.name = data["name"]
            tutor.surname = data["surname"]
            tutor.patronymic = data.get("patronymic")
            await session.commit()
    
    await callback_query.message.edit_text(
        "✅ Имя, фамилия и отчество успешно обновлены!",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

async def edit_profile_subjects(callback_query: types.CallbackQuery, state: FSMContext):
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            await state.update_data(subjects=tutor.subjects)
            await callback_query.message.edit_text(
                "📚 Выберите предметы и типы занятий:",
                reply_markup=get_profile_subjects_keyboard(tutor.subjects)
            )
            await state.set_state(ProfileEditing.editing_subjects)

async def process_subject_selection(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_subjects.state:
        return
    
    callback_data = callback_query.data
    
    # Игнорируем нажатие на название предмета
    if callback_data.startswith("subject_name_"):
        return
        
    # Обрабатываем выбор типа занятия
    if not callback_data.startswith("profile_subject_"):
        return
        
    # profile_subject_Математика_exam или profile_subject_Математика_standard
    _, _, subject, type_str = callback_data.split("_", 3)
    is_exam = type_str == "exam"
    
    data = await state.get_data()
    subjects = data.get("subjects", [])
    
    # Ищем предмет в списке
    subject_data = next(
        (s for s in subjects if s["name"] == subject),
        {"name": subject, "is_exam": False, "is_standard": False}
    )
    
    # Обновляем соответствующий флаг
    if is_exam:
        subject_data["is_exam"] = not subject_data["is_exam"]
    else:
        subject_data["is_standard"] = not subject_data["is_standard"]
    
    # Если предмета еще нет в списке, добавляем
    if subject_data not in subjects:
        subjects.append(subject_data)
    # Если оба флага False, удаляем предмет из списка
    elif not subject_data["is_exam"] and not subject_data["is_standard"]:
        subjects.remove(subject_data)
    
    await state.update_data(subjects=subjects)
    await callback_query.message.edit_text(
        "📚 Выберите предметы и типы занятий:",
        reply_markup=get_profile_subjects_keyboard(subjects)
    )

async def save_profile_subjects(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_subjects.state:
        return
        
    data = await state.get_data()
    subjects = data.get("subjects", [])
    
    # Проверяем, что хотя бы один предмет выбран с хотя бы одним типом
    if not any(s["is_exam"] or s["is_standard"] for s in subjects):
        await callback_query.answer("❌ Пожалуйста, выберите хотя бы один предмет и тип занятий!")
        return
    
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            tutor.subjects = subjects
            await session.commit()
    
    await callback_query.message.edit_text(
        "✅ Предметы успешно обновлены!",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

async def edit_profile_description(callback_query: types.CallbackQuery, state: FSMContext):
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            await state.update_data(description=tutor.description)
            await callback_query.message.edit_text(
                "📝 Напишите новое описание о себе, своем опыте преподавания и методике обучения:",
                reply_markup=get_profile_description_keyboard()
            )
            await state.set_state(ProfileEditing.editing_description)

async def cancel_description_edit(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "Редактирование описания отменено",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

async def save_profile_description(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_description.state:
        return
        
    data = await state.get_data()
    if not data.get("description"):
        await callback_query.answer("Пожалуйста, введите описание!")
        return
    
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            tutor.description = data["description"]
            await session.commit()
    
    await callback_query.message.edit_text(
        "✅ Описание успешно обновлено!",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

async def process_description_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_description.state:
        return
        
    await state.update_data(description=message.text)
    await message.answer(
        "Проверьте описание и нажмите 'Сохранить' или 'Отмена':",
        reply_markup=get_profile_description_keyboard()
    )

async def edit_profile_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            await state.update_data(schedule=tutor.schedule)
            await callback_query.message.edit_text(
                "🕒 Редактирование расписания\n📅 Выберите рабочие дни и задайте время работы:",
                reply_markup=get_profile_schedule_keyboard(tutor.schedule)
            )
            await state.set_state(ProfileEditing.editing_schedule)

async def toggle_profile_day_status(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_schedule.state:
        return
        
    day_code = callback_query.data.replace("profile_toggle_", "")
    data = await state.get_data()
    schedule = data.get("schedule", {})
    schedule[day_code]["active"] = not schedule[day_code]["active"]
    if not schedule[day_code]["active"]:
        schedule[day_code]["start"] = ""
        schedule[day_code]["end"] = ""
    await state.update_data(schedule=schedule)
    await callback_query.message.edit_reply_markup(
        reply_markup=get_profile_schedule_keyboard(schedule)
    )

async def set_profile_start_time(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_schedule.state:
        return
        
    day_code = callback_query.data.replace("profile_set_start_", "")
    await state.update_data(current_day=day_code, current_time_type="start")
    await callback_query.message.edit_text(
        f"Выберите час начала работы в {DAY_NAMES.get(day_code, day_code)}:",
        reply_markup=get_profile_hour_keyboard(day_code, "start")
    )

async def set_profile_end_time(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_schedule.state:
        return
        
    day_code = callback_query.data.replace("profile_set_end_", "")
    await state.update_data(current_day=day_code, current_time_type="end")
    await callback_query.message.edit_text(
        f"Выберите час окончания работы в {DAY_NAMES.get(day_code, day_code)}:",
        reply_markup=get_profile_hour_keyboard(day_code, "end")
    )

async def process_profile_hour(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_schedule.state:
        return
        
    # Исправляем парсинг callback-данных
    callback_data = callback_query.data
    if not callback_data.startswith("profile_hour_"):
        return
        
    # Разбираем callback_data на части
    # Формат: profile_hour_[start/end]_[day_code]_[hour]
    parts = callback_data.split("_")
    if len(parts) != 5:
        return
        
    time_type = parts[2]  # start или end
    day_code = parts[3]
    hour = int(parts[4])
    
    data = await state.get_data()
    schedule = data.get("schedule", {})
    if day_code not in schedule:
        schedule[day_code] = {"active": True, "start": "", "end": ""}
    await state.update_data(schedule=schedule, selected_hour=hour)
    
    time_text = "начала" if time_type == "start" else "окончания"
    await callback_query.message.edit_text(
        f"Выберите минуты для времени {time_text} работы в {DAY_NAMES.get(day_code, day_code)}:",
        reply_markup=get_profile_minute_keyboard(day_code, time_type, hour)
    )

async def process_profile_minute(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_schedule.state:
        return
        
    # Исправляем парсинг callback-данных
    callback_data = callback_query.data
    if not callback_data.startswith("profile_minute_"):
        return
        
    # Разбираем callback_data на части
    # Формат: profile_minute_[start/end]_[day_code]_[hour]_[minute]
    parts = callback_data.split("_")
    if len(parts) != 6:
        return
        
    time_type = parts[2]  # start или end
    day_code = parts[3]
    hour = int(parts[4])
    minute = int(parts[5])
    
    data = await state.get_data()
    schedule = data.get("schedule", {})
    if day_code not in schedule:
        schedule[day_code] = {"active": True, "start": "", "end": ""}
    time_str = f"{hour:02d}:{minute:02d}"
    schedule[day_code][time_type] = time_str
    schedule[day_code]["active"] = True
    
    # Проверяем корректность времени
    if time_type == "end" and schedule[day_code]["start"] and time_str <= schedule[day_code]["start"]:
        await callback_query.answer("Время окончания должно быть позже времени начала!")
        return
    elif time_type == "start" and schedule[day_code]["end"] and time_str >= schedule[day_code]["end"]:
        await callback_query.answer("Время начала должно быть раньше времени окончания!")
        return
    
    await state.update_data(schedule=schedule)
    await callback_query.message.edit_text(
        "🕒 Редактирование расписания\n📅 Выберите рабочие дни и задайте время работы:",
        reply_markup=get_profile_schedule_keyboard(schedule)
    )

async def cancel_schedule_edit(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "Редактирование расписания отменено",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

async def cancel_time_edit(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    schedule = data.get("schedule", {})
    await callback_query.message.edit_text(
        "🕒 Редактирование расписания\n📅 Выберите рабочие дни и задайте время работы:",
        reply_markup=get_profile_schedule_keyboard(schedule)
    )

async def save_profile_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_schedule.state:
        return
        
    data = await state.get_data()
    schedule = data.get("schedule", {})
    
    # Валидация расписания
    for day_code, info in schedule.items():
        if info["active"]:
            if not info["start"] or not info["end"]:
                await callback_query.answer(f"❌ Укажите время для {DAY_NAMES.get(day_code, day_code)}")
                return
            if info["end"] <= info["start"]:
                await callback_query.answer(f"❌ Время окончания должно быть позже начала для {DAY_NAMES.get(day_code, day_code)}")
                return
    
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            tutor.schedule = schedule
            await session.commit()
    
    await callback_query.message.edit_text(
        "✅ Расписание успешно обновлено!",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

async def edit_profile_prices(callback_query: types.CallbackQuery, state: FSMContext):
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            await state.update_data(subjects=tutor.subjects)
            await callback_query.message.edit_text(
                "💰 Установите цены для каждого типа занятий:\n"
                "Нажмите на цену, чтобы изменить её",
                reply_markup=get_profile_prices_keyboard(tutor.subjects)
            )
            await state.set_state(ProfileEditing.editing_prices)

async def process_price_edit(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_prices.state:
        return
        
    # price_edit_Математика_exam или price_edit_Математика_standard
    _, _, subject, price_type = callback_query.data.split("_", 3)
    
    await state.update_data(
        current_subject=subject,
        current_price_type=price_type
    )
    
    await callback_query.message.edit_text(
        f"💰 Введите новую цену для {subject} ({'ОГЭ/ЕГЭ' if price_type == 'exam' else 'Стандарт'}):\n"
        "Цена указывается в рублях за час (только число)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="price_cancel_edit")]
        ])
    )
    await state.set_state(ProfileEditing.waiting_for_price_input)

async def process_price_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.waiting_for_price_input.state:
        return
        
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError("Цена должна быть положительным числом")
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректную цену (положительное целое число):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="price_cancel_edit")]
            ])
        )
        return
    
    data = await state.get_data()
    subjects = data.get("subjects", [])
    subject = data.get("current_subject")
    price_type = data.get("current_price_type")
    
    # Обновляем цену
    for subject_data in subjects:
        if subject_data["name"] == subject:
            if price_type == "exam":
                subject_data["exam_price"] = price
            else:
                subject_data["standard_price"] = price
            break
    
    await state.update_data(subjects=subjects)
    await state.set_state(ProfileEditing.editing_prices)
    await message.answer(
        "💰 Установите цены для каждого типа занятий:\n"
        "Нажмите на цену, чтобы изменить её",
        reply_markup=get_profile_prices_keyboard(subjects)
    )

async def cancel_price_input(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена ввода цены и возврат к таблице цен"""
    current_state = await state.get_state()
    if current_state != ProfileEditing.waiting_for_price_input.state:
        return
        
    data = await state.get_data()
    subjects = data.get("subjects", [])
    await state.set_state(ProfileEditing.editing_prices)  # Возвращаемся к состоянию редактирования цен
    await callback_query.message.edit_text(
        "💰 Установите цены для каждого типа занятий:\n"
        "Нажмите на цену, чтобы изменить её",
        reply_markup=get_profile_prices_keyboard(subjects)
    )

async def cancel_prices_edit(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена редактирования цен и возврат к меню профиля"""
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_prices.state:
        return
        
    await callback_query.message.edit_text(
        "📝 Выберите, что хотите изменить:",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

async def save_profile_prices(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != ProfileEditing.editing_prices.state:
        return
        
    data = await state.get_data()
    subjects = data.get("subjects", [])
    
    # Проверяем, что все активные типы занятий имеют цены
    for subject in subjects:
        if subject["is_exam"] and not subject.get("exam_price"):
            await callback_query.answer(f"❌ Укажите цену для ОГЭ/ЕГЭ по предмету {subject['name']}")
            return
        if subject["is_standard"] and not subject.get("standard_price"):
            await callback_query.answer(f"❌ Укажите цену для Стандарт по предмету {subject['name']}")
            return
    
    async for session in get_session():
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        if tutor:
            tutor.subjects = subjects
            await session.commit()
    
    await callback_query.message.edit_text(
        "✅ Цены успешно обновлены!",
        reply_markup=get_profile_menu_keyboard()
    )
    await state.clear()

def register_profile_handlers(dp):
    dp.callback_query.register(show_profile, lambda c: c.data == "my_profile")
    dp.callback_query.register(show_edit_menu, lambda c: c.data == "edit_profile")
    dp.callback_query.register(back_to_main_menu, lambda c: c.data == "back_to_main")
    
    # Обработчики для редактирования имени, фамилии и отчества
    dp.callback_query.register(edit_profile_name, lambda c: c.data == "edit_profile_name")
    dp.callback_query.register(process_edit_name, lambda c: c.data == "profile_edit_name")
    dp.callback_query.register(process_edit_surname, lambda c: c.data == "profile_edit_surname")
    dp.callback_query.register(process_edit_patronymic, lambda c: c.data == "profile_edit_patronymic")
    dp.callback_query.register(cancel_patronymic_edit, lambda c: c.data == "profile_cancel_patronymic")
    dp.message.register(process_name_input, ProfileEditing.editing_name)
    dp.message.register(process_surname_input, ProfileEditing.editing_surname)
    dp.message.register(process_patronymic_input, ProfileEditing.editing_patronymic)
    dp.callback_query.register(save_profile_name_surname, lambda c: c.data == "profile_save_name_surname")
    
    # Обработчики для редактирования предметов
    dp.callback_query.register(edit_profile_subjects, lambda c: c.data == "edit_profile_subjects")
    dp.callback_query.register(process_subject_selection, lambda c: c.data.startswith("profile_subject_"))
    dp.callback_query.register(save_profile_subjects, lambda c: c.data == "profile_save_subjects")
    
    # Обработчики для редактирования описания
    dp.callback_query.register(edit_profile_description, lambda c: c.data == "edit_profile_description")
    dp.callback_query.register(cancel_description_edit, lambda c: c.data == "profile_cancel_description")
    dp.callback_query.register(save_profile_description, lambda c: c.data == "profile_save_description")
    dp.message.register(process_description_input, ProfileEditing.editing_description)
    
    # Обработчики для редактирования расписания
    dp.callback_query.register(edit_profile_schedule, lambda c: c.data == "edit_profile_schedule")
    dp.callback_query.register(toggle_profile_day_status, lambda c: c.data.startswith("profile_toggle_"))
    dp.callback_query.register(set_profile_start_time, lambda c: c.data.startswith("profile_set_start_"))
    dp.callback_query.register(set_profile_end_time, lambda c: c.data.startswith("profile_set_end_"))
    dp.callback_query.register(process_profile_hour, lambda c: c.data.startswith("profile_hour_"))
    dp.callback_query.register(process_profile_minute, lambda c: c.data.startswith("profile_minute_"))
    dp.callback_query.register(cancel_schedule_edit, lambda c: c.data == "profile_cancel_schedule")
    dp.callback_query.register(cancel_time_edit, lambda c: c.data == "profile_cancel_time")
    dp.callback_query.register(save_profile_schedule, lambda c: c.data == "profile_save_schedule")
    
    # Обработчики для редактирования цен
    dp.callback_query.register(edit_profile_prices, lambda c: c.data == "edit_profile_prices")
    dp.callback_query.register(process_price_edit, lambda c: c.data.startswith("price_edit_"))
    dp.callback_query.register(cancel_price_input, lambda c: c.data == "price_cancel_edit")
    dp.callback_query.register(cancel_prices_edit, lambda c: c.data == "price_cancel")
    dp.callback_query.register(save_profile_prices, lambda c: c.data == "price_save")
    dp.message.register(process_price_input, ProfileEditing.waiting_for_price_input) 