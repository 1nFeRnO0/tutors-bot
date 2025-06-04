from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from common.database import Tutor, get_session
from tutor_bot.keyboards import (
    get_registration_form_keyboard,
    get_subjects_keyboard,
    get_schedule_table,
    get_hour_keyboard,
    get_minute_keyboard,
    DAY_NAMES,
    get_registration_prices_keyboard,
    get_registration_description_keyboard
)

from tutor_bot.handlers.profile import show_profile

class TutorRegistration(StatesGroup):
    waiting_for_name_surname = State()
    waiting_for_name_input = State()
    waiting_for_surname_input = State()
    waiting_for_patronymic_input = State()
    waiting_for_subjects = State()
    waiting_for_description = State()
    waiting_for_schedule_table = State()
    waiting_for_time_hour = State()
    waiting_for_time_minute = State()
    setting_prices = State()
    waiting_for_price_input = State()

async def process_start_registration(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard()
    )
    await state.set_state(TutorRegistration.waiting_for_name_surname)

async def process_edit_name(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == TutorRegistration.waiting_for_name_surname.state:
        await callback_query.message.edit_text("Как тебя зовут?")
        await state.set_state(TutorRegistration.waiting_for_name_input)

async def process_edit_surname(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == TutorRegistration.waiting_for_name_surname.state:
        await callback_query.message.edit_text("Какая у тебя фамилия?")
        await state.set_state(TutorRegistration.waiting_for_surname_input)

async def process_edit_patronymic(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == TutorRegistration.waiting_for_name_surname.state:
        await callback_query.message.edit_text(
            "Какое у тебя отчество? (Если отчества нет, просто нажми 'Продолжить')",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Продолжить без отчества", callback_data="skip_patronymic")]
            ])
        )
        await state.set_state(TutorRegistration.waiting_for_patronymic_input)

async def process_name_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(name=message.text)
    await message.answer(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard(name=message.text, surname=data.get("surname", ""))
    )
    await state.set_state(TutorRegistration.waiting_for_name_surname)

async def process_surname_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(surname=message.text)
    await message.answer(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard(name=data.get("name", ""), surname=message.text)
    )
    await state.set_state(TutorRegistration.waiting_for_name_surname)

async def process_patronymic_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(patronymic=message.text)
    await message.answer(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard(
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            patronymic=message.text
        )
    )
    await state.set_state(TutorRegistration.waiting_for_name_surname)

async def process_finish_name_surname(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("name") or not data.get("surname"):
        await callback_query.answer("Пожалуйста, заполните имя и фамилию!")
        return
    
    await callback_query.message.edit_text(
        "Отлично! Теперь выберите предметы, которые вы преподаете:",
        reply_markup=get_subjects_keyboard([])
    )
    await state.set_state(TutorRegistration.waiting_for_subjects)

async def process_subject_selection(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != TutorRegistration.waiting_for_subjects.state:
        return
    
    callback_data = callback_query.data
    
    # Игнорируем нажатие на название предмета
    if callback_data.startswith("subject_name_"):
        return
        
    # Обрабатываем выбор типа занятия
    if not callback_data.startswith("subject_"):
        return
        
    # subject_Математика_exam или subject_Математика_standard
    _, subject, type_str = callback_data.split("_", 2)
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
        "Выберите предметы и типы занятий:",
        reply_markup=get_subjects_keyboard(subjects)
    )

async def process_finish_subjects(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    subjects = data.get("subjects", [])
    
    # Проверяем, что хотя бы один предмет выбран с хотя бы одним типом
    if not any(s["is_exam"] or s["is_standard"] for s in subjects):
        await callback_query.answer("Пожалуйста, выберите хотя бы один предмет и тип занятий!")
        return
    
    await callback_query.message.edit_text(
        "💰 Установите цены для каждого типа занятий:\n"
        "Нажмите на цену, чтобы изменить её",
        reply_markup=get_registration_prices_keyboard(subjects)
    )
    await state.set_state(TutorRegistration.setting_prices)

async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    # Инициализируем расписание по умолчанию
    schedule = {day_code: {"active": False, "start": "", "end": ""} for day_code in DAY_NAMES.keys()}
    await state.update_data(schedule=schedule)
    await message.answer(
        "Расписание\nВыбери рабочие дни и задай начало и окончание рабочего времени.",
        reply_markup=get_schedule_table(schedule)
    )
    await state.set_state(TutorRegistration.waiting_for_schedule_table)

async def toggle_day_status(callback_query: types.CallbackQuery, state: FSMContext):
    day_code = callback_query.data.replace("toggle_", "")
    data = await state.get_data()
    schedule = data.get("schedule", {})
    schedule[day_code]["active"] = not schedule[day_code]["active"]
    if not schedule[day_code]["active"]:
        schedule[day_code]["start"] = ""
        schedule[day_code]["end"] = ""
    await state.update_data(schedule=schedule)
    await callback_query.message.edit_reply_markup(reply_markup=get_schedule_table(schedule))

async def process_hour(callback_query: types.CallbackQuery, state: FSMContext):
    parts = callback_query.data.split("_")
    time_type = parts[1]  # start или end
    day_code = parts[3]
    hour = int(parts[4])
    data = await state.get_data()
    schedule = data.get("schedule", {})
    if day_code not in schedule:
        schedule[day_code] = {"active": True, "start": "", "end": ""}
    await state.update_data(schedule=schedule, selected_hour=hour)
    
    time_text = "начала" if time_type == "start" else "окончания"
    await callback_query.message.edit_text(
        f"Выбери минуты для времени {time_text} работы в {DAY_NAMES.get(day_code, day_code)}:",
        reply_markup=get_minute_keyboard(day_code, time_type, hour)
    )
    await state.set_state(TutorRegistration.waiting_for_time_minute)

async def process_minute(callback_query: types.CallbackQuery, state: FSMContext):
    parts = callback_query.data.split("_")
    time_type = parts[1]  # start или end
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
        "Расписание\nВыбери рабочие дни и задай начало и окончание рабочего времени.",
        reply_markup=get_schedule_table(schedule)
    )
    await state.set_state(TutorRegistration.waiting_for_schedule_table)

async def set_start_time(callback_query: types.CallbackQuery, state: FSMContext):
    day_code = callback_query.data.replace("set_start_", "")
    await state.update_data(current_day=day_code, current_time_type="start")
    await callback_query.message.edit_text(
        f"В котором часу ты начинаешь работу в {DAY_NAMES.get(day_code, day_code)}? Выбери часы, затем сможешь выбрать минуты.",
        reply_markup=get_hour_keyboard(day_code, "start")
    )
    await state.set_state(TutorRegistration.waiting_for_time_hour)

async def set_end_time(callback_query: types.CallbackQuery, state: FSMContext):
    day_code = callback_query.data.replace("set_end_", "")
    await state.update_data(current_day=day_code, current_time_type="end")
    await callback_query.message.edit_text(
        f"В котором часу ты заканчиваешь работу в {DAY_NAMES.get(day_code, day_code)}? Выбери часы, затем сможешь выбрать минуты.",
        reply_markup=get_hour_keyboard(day_code, "end")
    )
    await state.set_state(TutorRegistration.waiting_for_time_hour)

async def back_to_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    schedule = data.get("schedule", {})
    await callback_query.message.edit_text(
        "Расписание\nВыбери рабочие дни и задай начало и окончание рабочего времени.",
        reply_markup=get_schedule_table(schedule)
    )
    await state.set_state(TutorRegistration.waiting_for_schedule_table)

async def save_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    schedule = data.get("schedule", {})
    # Валидация: для активных дней start и end должны быть заданы и end > start
    for day_code, info in schedule.items():
        if info["active"]:
            if not info["start"] or not info["end"]:
                await callback_query.answer(f"Укажите время для {DAY_NAMES.get(day_code, day_code)}")
                return
            if info["end"] <= info["start"]:
                await callback_query.answer(f"Время окончания должно быть позже начала для {DAY_NAMES.get(day_code, day_code)}")
                return
    
    async for session in get_session():
        tutor = Tutor(
            telegram_id=callback_query.from_user.id,
            name=data["name"],
            surname=data["surname"],
            patronymic=data.get("patronymic"),
            subjects=data["subjects"],
            schedule=schedule,
            description=data["description"]
        )
        session.add(tutor)
        await session.commit()
    
    await callback_query.message.edit_text(
        "🎉 Регистрация завершена! Ваше расписание и данные сохранены."
    )
    await state.clear()
    await show_profile(callback_query)

async def process_registration_price_edit(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != TutorRegistration.setting_prices.state:
        return
        
    # registration_price_edit_Математика_exam или registration_price_edit_Математика_standard
    _, _, _, subject, price_type = callback_query.data.split("_", 4)
    
    await state.update_data(
        current_subject=subject,
        current_price_type=price_type
    )
    
    await callback_query.message.edit_text(
        f"💰 Введите цену для {subject} ({'ОГЭ/ЕГЭ' if price_type == 'exam' else 'Стандарт'}):\n"
        "Цена указывается в рублях за час (только число)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="registration_price_cancel_edit")]
        ])
    )
    await state.set_state(TutorRegistration.waiting_for_price_input)

async def process_registration_price_input(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != TutorRegistration.waiting_for_price_input.state:
        return
        
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError("Цена должна быть положительным числом")
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректную цену (положительное целое число):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Отмена", callback_data="registration_price_cancel_edit")]
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
    await state.set_state(TutorRegistration.setting_prices)
    await message.answer(
        "💰 Установите цены для каждого типа занятий:\n"
        "Нажмите на цену, чтобы изменить её",
        reply_markup=get_registration_prices_keyboard(subjects)
    )

async def cancel_registration_price_edit(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != TutorRegistration.waiting_for_price_input.state:
        return
        
    data = await state.get_data()
    subjects = data.get("subjects", [])
    await state.set_state(TutorRegistration.setting_prices)  # Возвращаемся к состоянию настройки цен
    await callback_query.message.edit_text(
        "💰 Установите цены для каждого типа занятий:\n"
        "Нажмите на цену, чтобы изменить её",
        reply_markup=get_registration_prices_keyboard(subjects)
    )

async def back_to_subjects(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    subjects = data.get("subjects", [])
    await callback_query.message.edit_text(
        "Выберите предметы и типы занятий:",
        reply_markup=get_subjects_keyboard(subjects)
    )
    await state.set_state(TutorRegistration.waiting_for_subjects)

async def save_registration_prices(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != TutorRegistration.setting_prices.state:
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
    
    # Переходим к следующему шагу регистрации
    await callback_query.message.edit_text(
        "Напишите описание о себе, своем опыте преподавания и методике обучения:",
        reply_markup=get_registration_description_keyboard()
    )
    await state.set_state(TutorRegistration.waiting_for_description)

async def back_to_prices(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    subjects = data.get("subjects", [])
    await callback_query.message.edit_text(
        "💰 Установите цены для каждого типа занятий:\n"
        "Нажмите на цену, чтобы изменить её",
        reply_markup=get_registration_prices_keyboard(subjects)
    )
    await state.set_state(TutorRegistration.setting_prices)

async def skip_patronymic(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback_query.message.edit_text(
        "Заполните информацию о себе:",
        reply_markup=get_registration_form_keyboard(
            name=data.get("name", ""),
            surname=data.get("surname", ""),
            patronymic=""
        )
    )
    await state.set_state(TutorRegistration.waiting_for_name_surname)

def register_registration_handlers(dp):
    dp.callback_query.register(process_start_registration, lambda c: c.data == "start_registration")
    dp.callback_query.register(process_edit_name, lambda c: c.data == "edit_name")
    dp.callback_query.register(process_edit_surname, lambda c: c.data == "edit_surname")
    dp.callback_query.register(process_edit_patronymic, lambda c: c.data == "edit_patronymic")
    dp.message.register(process_name_input, TutorRegistration.waiting_for_name_input)
    dp.message.register(process_surname_input, TutorRegistration.waiting_for_surname_input)
    dp.callback_query.register(process_finish_name_surname, lambda c: c.data == "finish_name_surname")
    dp.callback_query.register(process_subject_selection, lambda c: c.data.startswith("subject_"))
    dp.callback_query.register(process_finish_subjects, lambda c: c.data == "registration_finish_subjects")
    dp.message.register(process_description, TutorRegistration.waiting_for_description)
    dp.callback_query.register(toggle_day_status, lambda c: c.data.startswith("toggle_"))
    dp.callback_query.register(process_hour, lambda c: c.data.startswith("set_start_hour_") or c.data.startswith("set_end_hour_"))
    dp.callback_query.register(process_minute, lambda c: c.data.startswith("set_start_minute_") or c.data.startswith("set_end_minute_"))
    dp.callback_query.register(set_start_time, lambda c: c.data.startswith("set_start_"))
    dp.callback_query.register(set_end_time, lambda c: c.data.startswith("set_end_"))
    dp.callback_query.register(back_to_schedule, lambda c: c.data == "back_to_schedule")
    dp.callback_query.register(save_schedule, lambda c: c.data == "save_schedule")
    dp.callback_query.register(process_registration_price_edit, lambda c: c.data.startswith("registration_price_edit_"))
    dp.callback_query.register(cancel_registration_price_edit, lambda c: c.data == "registration_price_cancel_edit")
    dp.message.register(process_registration_price_input, TutorRegistration.waiting_for_price_input)
    dp.callback_query.register(save_registration_prices, lambda c: c.data == "registration_price_save")
    dp.callback_query.register(back_to_subjects, lambda c: c.data == "registration_price_back")
    dp.callback_query.register(back_to_prices, lambda c: c.data == "registration_description_back")
    dp.message.register(process_patronymic_input, TutorRegistration.waiting_for_patronymic_input)
    dp.callback_query.register(skip_patronymic, lambda c: c.data == "skip_patronymic") 