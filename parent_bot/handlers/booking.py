from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List

from common.database import Parent, Child, Tutor, Booking, FavoriteTutor, async_session_maker
from parent_bot.booking_kb import (
    get_children_keyboard,
    get_tutors_keyboard,
    get_subjects_keyboard,
    get_lesson_type_keyboard,
    create_calendar_keyboard,
    get_time_slots_keyboard,
    get_booking_confirmation_keyboard
)

# Константы для длительности занятий (в минутах)
LESSON_DURATIONS = {
    'standard': 60,
    'exam': 90
}

class BookingStates(StatesGroup):
    """Состояния для процесса бронирования занятия"""
    waiting_for_child = State()
    waiting_for_tutor = State()
    waiting_for_subject = State()
    waiting_for_lesson_type = State()
    waiting_for_date = State()
    waiting_for_time = State()
    confirmation = State()

async def calculate_available_slots(
    tutor_schedule: dict,
    existing_bookings: list,
    lesson_duration: int,
    date: datetime.date
) -> List[tuple]:
    """
    Рассчитывает доступные слоты для записи на конкретную дату
    
    Args:
        tutor_schedule (dict): Расписание репетитора
        existing_bookings (list): Список существующих бронирований на эту дату
        lesson_duration (int): Длительность занятия в минутах
        date (datetime.date): Дата, на которую проверяются слоты
    
    Returns:
        List[tuple]: Список доступных временных слотов в формате [(start_time, end_time), ...]
    """
    weekday = date.strftime('%A').lower()
    if weekday not in tutor_schedule:
        return []
    
    # Получаем расписание на этот день недели
    day_schedule = tutor_schedule[weekday]
    
    # Проверяем, активен ли этот день и есть ли временной интервал
    if not isinstance(day_schedule, dict) or \
       not day_schedule.get('active') or \
       not day_schedule.get('start') or \
       not day_schedule.get('end'):
        return []
        
    available_slots = []
    
    # Преобразуем существующие записи в список занятых интервалов
    busy_slots = []
    for booking in existing_bookings:
        busy_slots.append((booking.start_time, booking.end_time))
    
    # Сортируем занятые слоты по времени начала
    busy_slots.sort(key=lambda x: x[0])
    
    try:
        # Парсим время начала и конца рабочего дня
        start_time = datetime.strptime(day_schedule['start'].strip(), '%H:%M').time()
        end_time = datetime.strptime(day_schedule['end'].strip(), '%H:%M').time()
        
        current_time = start_time
        while True:
            # Создаем временной слот для проверки
            slot_end_time = (
                datetime.combine(date, current_time) + 
                timedelta(minutes=lesson_duration)
            ).time()
            
            # Если конец слота выходит за пределы рабочего времени, прерываем
            if slot_end_time > end_time:
                break
            
            # Проверяем, не пересекается ли слот с существующими записями
            is_available = True
            for busy_start, busy_end in busy_slots:
                if (current_time < busy_end and 
                    slot_end_time > busy_start):
                    is_available = False
                    break
            
            if is_available:
                available_slots.append((current_time, slot_end_time))
            
            # Переходим к следующему возможному началу занятия
            # (используем шаг в 30 минут)
            current_time = (
                datetime.combine(date, current_time) + 
                timedelta(minutes=30)
            ).time()
            
            if current_time >= end_time:
                break
                
    except ValueError as e:
        print(f"Error processing schedule for {weekday}: {str(e)}")
        return []
    
    return available_slots

async def is_date_available(date: datetime.date, tutor_id: int, lesson_duration: int) -> bool:
    """
    Проверяет, доступна ли дата для записи
    
    Args:
        date (datetime.date): Проверяемая дата
        tutor_id (int): ID репетитора
        lesson_duration (int): Длительность занятия в минутах
    
    Returns:
        bool: True если дата доступна, False если нет
    """
    # TODO: Реализовать проверку доступности даты
    pass

async def show_bookings(callback_query: types.CallbackQuery):
    """Показывает список записей пользователя"""
    async with async_session_maker() as session:
        # Получаем родителя со всеми связанными данными
        parent = await session.execute(
            select(Parent)
            .options(
                selectinload(Parent.bookings)
                .selectinload(Booking.child),
                selectinload(Parent.bookings)
                .selectinload(Booking.tutor)
            )
            .where(Parent.telegram_id == callback_query.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent or not parent.bookings:
            # Если записей нет, показываем сообщение и кнопку создания
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Записаться на занятие", callback_data="start_booking")],
                [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
            ])
            await callback_query.message.edit_text(
                "У вас пока нет записей на занятия. Нажмите кнопку ниже, чтобы записаться:",
                reply_markup=keyboard
            )
            return
        
        # Формируем список активных записей
        active_bookings = [b for b in parent.bookings if b.status == 'active']
        
        if not active_bookings:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Записаться на занятие", callback_data="start_booking")],
                [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
            ])
            await callback_query.message.edit_text(
                "У вас нет активных записей на занятия. Нажмите кнопку ниже, чтобы записаться:",
                reply_markup=keyboard
            )
            return
        
        # Формируем текст со списком записей
        text = "Ваши активные записи:\n\n"
        keyboard = []
        
        for booking in active_bookings:
            # Формируем строку с информацией о записи
            booking_info = (
                f"📚 {booking.subject_name}\n"
                f"👤 Ученик: {booking.child.name} {booking.child.surname}\n"
                f"👨‍🏫 Репетитор: {booking.tutor.name} {booking.tutor.surname}\n"
                f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
                f"🕒 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
                f"💰 Стоимость: {booking.price} ₽\n"
                f"📋 Тип: {'Подготовка к экзамену' if booking.lesson_type == 'exam' else 'Стандартное занятие'}\n"
                "-------------------\n"
            )
            text += booking_info
            
            # Добавляем кнопку отмены для каждой записи
            keyboard.append([
                InlineKeyboardButton(
                    text=f"❌ Отменить запись на {booking.date.strftime('%d.%m.%Y')} {booking.start_time.strftime('%H:%M')}",
                    callback_data=f"cancel_booking_{booking.id}"
                )
            ])
        
        # Добавляем кнопки управления
        keyboard.extend([
            [InlineKeyboardButton(text="📝 Записаться на занятие", callback_data="start_booking")],
            [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
        ])
        
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

async def start_booking(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает процесс бронирования занятия"""
    async with async_session_maker() as session:
        # Получаем данные о родителе
        parent = await session.execute(
            select(Parent)
            .options(selectinload(Parent.children))
            .where(Parent.telegram_id == callback_query.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent or not parent.children:
            await callback_query.message.edit_text(
                "У вас нет добавленных детей. Сначала добавьте ребенка в разделе 'Мои дети'.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return

        # Сохраняем ID родителя в состоянии
        await state.update_data(parent_id=parent.id)
        
        # Создаем клавиатуру с детьми
        keyboard = get_children_keyboard(parent.children)
        
        # Отправляем сообщение с выбором ребенка
        await callback_query.message.edit_text(
            "Выберите ребенка для записи на занятие:",
            reply_markup=keyboard
        )
        
        # Устанавливаем состояние ожидания выбора ребенка
        await state.set_state(BookingStates.waiting_for_child)

async def process_child_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор ребенка"""
    child_id = int(callback_query.data.split('_')[-1])
    
    async with async_session_maker() as session:
        # Получаем данные о ребенке
        child = await session.execute(
            select(Child).where(Child.id == child_id)
        )
        child = child.scalar_one_or_none()
        
        if not child:
            await callback_query.message.edit_text(
                "Ошибка: ребенок не найден. Попробуйте начать сначала.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Сохраняем ID ребенка в данных состояния
        await state.update_data(child_id=child_id)
        
        # Получаем список репетиторов родителя
        parent = await session.execute(
            select(Parent)
            .options(selectinload(Parent.favorite_tutors).selectinload(FavoriteTutor.tutor))
            .where(Parent.telegram_id == callback_query.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent or not parent.favorite_tutors:
            await callback_query.message.edit_text(
                "У вас нет добавленных репетиторов. Сначала добавьте репетиторов в разделе 'Мои репетиторы'.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Создаем клавиатуру с репетиторами
        tutors = [ft.tutor for ft in parent.favorite_tutors]
        keyboard = get_tutors_keyboard(tutors)
        
        # Отправляем сообщение с выбором репетитора
        await callback_query.message.edit_text(
            f"Выберите репетитора для {child.name}:",
            reply_markup=keyboard
        )
        
        # Переходим к следующему состоянию
        await state.set_state(BookingStates.waiting_for_tutor)

async def process_tutor_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор репетитора"""
    tutor_id = int(callback_query.data.split('_')[-1])
    
    async with async_session_maker() as session:
        # Получаем данные о репетиторе
        tutor = await session.execute(
            select(Tutor).where(Tutor.id == tutor_id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if not tutor:
            await callback_query.message.edit_text(
                "Ошибка: репетитор не найден. Попробуйте начать сначала.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Сохраняем ID репетитора и его предметы в данных состояния
        await state.update_data(tutor_id=tutor_id, subjects=tutor.subjects)
        
        # Получаем список предметов репетитора
        subjects = tutor.subjects
        if not subjects or not any(subj.get('is_standard') or subj.get('is_exam') for subj in subjects):
            await callback_query.message.edit_text(
                "У выбранного репетитора нет доступных предметов. Попробуйте выбрать другого репетитора.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад к выбору репетитора", callback_data="back_to_tutor_selection")],
                    [InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_booking")]
                ])
            )
            return
        
        # Создаем клавиатуру с предметами
        keyboard = get_subjects_keyboard(subjects)
        
        # Получаем данные о ребенке для сообщения
        state_data = await state.get_data()
        child = await session.execute(
            select(Child).where(Child.id == state_data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        # Формируем текст с доступными типами занятий для каждого предмета
        subjects_info = "\n".join(
            f"📚 {subj['name']}: " + 
            ", ".join(filter(None, [
                "стандартное занятие" if subj.get('is_standard') else None,
                "подготовка к экзамену" if subj.get('is_exam') else None
            ]))
            for subj in subjects
            if subj.get('is_standard') or subj.get('is_exam')
        )
        
        # Отправляем сообщение с выбором предмета
        message_text = (
            f"Выберите предмет для занятия:\n"
            f"👤 Ученик: {child.name}\n"
            f"👨‍🏫 Репетитор: {tutor.name} {tutor.surname}\n\n"
            f"Доступные предметы и типы занятий:\n{subjects_info}"
        )
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard
        )
        
        # Переходим к следующему состоянию
        await state.set_state(BookingStates.waiting_for_subject)

async def process_subject_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор предмета"""
    subject_name = callback_query.data.split('_')[-1]
    state_data = await state.get_data()
    
    # Находим выбранный предмет в списке предметов репетитора
    subject = next(
        (subj for subj in state_data['subjects'] if subj['name'] == subject_name),
        None
    )
    
    if not subject:
        await callback_query.message.edit_text(
            "Ошибка: предмет не найден. Попробуйте начать сначала.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
            ])
        )
        await state.clear()
        return
    
    # Сохраняем выбранный предмет в состоянии
    await state.update_data(
        subject_name=subject_name,
        subject_info=subject
    )
    
    # Создаем клавиатуру только с доступными типами занятий
    keyboard = []
    if subject.get('is_standard'):
        keyboard.append([
            InlineKeyboardButton(
                text=f"📚 Стандартное занятие ({subject['standard_price']} ₽)",
                callback_data="book_type_standard"
            )
        ])
    if subject.get('is_exam'):
        keyboard.append([
            InlineKeyboardButton(
                text=f"📝 Подготовка к экзамену ({subject['exam_price']} ₽)",
                callback_data="book_type_exam"
            )
        ])
    
    # Добавляем кнопки навигации
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_tutor_selection")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking")])
    
    # Получаем информацию о ребенке и репетиторе для сообщения
    async with async_session_maker() as session:
        child = await session.execute(
            select(Child).where(Child.id == state_data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        tutor = await session.execute(
            select(Tutor).where(Tutor.id == state_data['tutor_id'])
        )
        tutor = tutor.scalar_one_or_none()
        
        if not child or not tutor:
            await callback_query.message.edit_text(
                "Ошибка: не удалось получить данные. Попробуйте начать сначала.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Формируем сообщение
        message_text = (
            f"Выберите тип занятия:\n\n"
            f"👤 Ученик: {child.name}\n"
            f"👨‍🏫 Репетитор: {tutor.name} {tutor.surname}\n"
            f"📚 Предмет: {subject_name}\n\n"
            f"Доступные типы занятий:"
        )
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
        # Переходим к следующему состоянию
        await state.set_state(BookingStates.waiting_for_lesson_type)

async def process_lesson_type_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа занятия"""
    lesson_type = callback_query.data.split('_')[-1]  # standard или exam
    state_data = await state.get_data()
    subject_info = state_data['subject_info']
    
    # Проверяем, доступен ли выбранный тип занятия
    if (lesson_type == 'standard' and not subject_info.get('is_standard')) or \
       (lesson_type == 'exam' and not subject_info.get('is_exam')):
        await callback_query.message.edit_text(
            "Ошибка: выбранный тип занятия недоступен для данного предмета.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к выбору предмета", callback_data="back_to_subject_selection")],
                [InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_booking")]
            ])
        )
        return
    
    # Сохраняем тип занятия и его стоимость
    price = subject_info.get(f'{lesson_type}_price', 0)
    await state.update_data(
        lesson_type=lesson_type,
        lesson_duration=LESSON_DURATIONS[lesson_type],
        price=price
    )
    
    async with async_session_maker() as session:
        # Получаем данные о ребенке и репетиторе
        child = await session.execute(
            select(Child).where(Child.id == state_data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        tutor = await session.execute(
            select(Tutor).where(Tutor.id == state_data['tutor_id'])
        )
        tutor = tutor.scalar_one_or_none()
        
        if not child or not tutor:
            await callback_query.message.edit_text(
                "Ошибка: не удалось получить данные. Попробуйте начать сначала.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Получаем текущую дату и создаем календарь на текущий месяц
        current_date = datetime.now().date()
        available_dates = await get_available_dates(
            tutor.schedule,
            tutor.id,
            LESSON_DURATIONS[lesson_type],
            current_date,
            current_date + timedelta(days=30)  # Показываем даты на месяц вперед
        )
        
        if not available_dates:
            await callback_query.message.edit_text(
                "К сожалению, у репетитора нет свободных слотов на ближайший месяц. "
                "Попробуйте выбрать другого репетитора или связаться с текущим для уточнения расписания.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад к выбору репетитора", callback_data="back_to_tutor_selection")],
                    [InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_booking")]
                ])
            )
            return
        
        # Создаем клавиатуру-календарь
        keyboard = create_calendar_keyboard(
            current_date.year,
            current_date.month,
            available_dates
        )
        
        # Формируем сообщение с информацией о выбранных параметрах
        message_text = (
            f"Выберите дату занятия:\n\n"
            f"👤 Ученик: {child.name}\n"
            f"👨‍🏫 Репетитор: {tutor.name} {tutor.surname}\n"
            f"📚 Предмет: {state_data['subject_name']}\n"
            f"📝 Тип занятия: {'Подготовка к экзамену' if lesson_type == 'exam' else 'Стандартное занятие'}\n"
            f"⏱ Длительность: {LESSON_DURATIONS[lesson_type]} минут\n"
            f"💰 Стоимость: {price} ₽\n\n"
            f"Выберите удобную дату в календаре:"
        )
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard
        )
        
        # Переходим к следующему состоянию
        await state.set_state(BookingStates.waiting_for_date)

async def get_available_dates(
    tutor_schedule: dict,
    tutor_id: int,
    lesson_duration: int,
    start_date: datetime.date,
    end_date: datetime.date
) -> List[datetime.date]:
    """
    Получает список доступных дат для записи

    Args:
        tutor_schedule (dict): Расписание репетитора
        tutor_id (int): ID репетитора
        lesson_duration (int): Длительность занятия
        start_date (datetime.date): Начальная дата
        end_date (datetime.date): Конечная дата

    Returns:
        List[datetime.date]: Список доступных дат
    """
    available_dates = []
    current_date = start_date

    async with async_session_maker() as session:
        while current_date <= end_date:
            # Проверяем, работает ли репетитор в этот день недели
            weekday = current_date.strftime('%A').lower()  # Получаем день недели в нижнем регистре
            if weekday in tutor_schedule:
                # Получаем существующие записи на эту дату
                existing_bookings = await session.execute(
                    select(Booking)
                    .where(
                        Booking.tutor_id == tutor_id,
                        Booking.date == current_date,
                        Booking.status == 'active'
                    )
                )
                existing_bookings = existing_bookings.scalars().all()

                # Проверяем, есть ли свободные слоты в этот день
                day_slots = await calculate_available_slots(
                    tutor_schedule,
                    existing_bookings,
                    lesson_duration,
                    current_date
                )

                if day_slots:  # Если есть свободные слоты
                    available_dates.append(current_date)

            current_date += timedelta(days=1)

    return available_dates

async def back_to_child_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Возвращает к выбору ребенка"""
    async with async_session_maker() as session:
        parent = await session.execute(
            select(Parent)
            .options(selectinload(Parent.children))
            .where(Parent.telegram_id == callback_query.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent or not parent.children:
            await callback_query.message.edit_text(
                "Ошибка: не удалось получить список детей.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Создаем клавиатуру с детьми
        keyboard = get_children_keyboard(parent.children)
        
        # Отправляем сообщение с выбором ребенка
        await callback_query.message.edit_text(
            "Выберите ребенка для записи на занятие:",
            reply_markup=keyboard
        )
        
        # Возвращаемся к состоянию выбора ребенка
        await state.set_state(BookingStates.waiting_for_child)

async def back_to_tutor_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Возвращает к выбору репетитора"""
    async with async_session_maker() as session:
        # Получаем список репетиторов родителя
        parent = await session.execute(
            select(Parent)
            .options(selectinload(Parent.favorite_tutors).selectinload(FavoriteTutor.tutor))
            .where(Parent.telegram_id == callback_query.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent or not parent.favorite_tutors:
            await callback_query.message.edit_text(
                "Ошибка: не удалось получить список репетиторов.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Получаем данные о ребенке для сообщения
        state_data = await state.get_data()
        child = await session.execute(
            select(Child).where(Child.id == state_data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        # Создаем клавиатуру с репетиторами
        tutors = [ft.tutor for ft in parent.favorite_tutors]
        keyboard = get_tutors_keyboard(tutors)
        
        # Отправляем сообщение с выбором репетитора
        await callback_query.message.edit_text(
            f"Выберите репетитора для {child.name}:",
            reply_markup=keyboard
        )
        
        # Возвращаемся к состоянию выбора репетитора
        await state.set_state(BookingStates.waiting_for_tutor)

async def back_to_subject_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Возвращает к выбору предмета"""
    state_data = await state.get_data()
    
    async with async_session_maker() as session:
        # Получаем данные о ребенке и репетиторе
        child = await session.execute(
            select(Child).where(Child.id == state_data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        tutor = await session.execute(
            select(Tutor).where(Tutor.id == state_data['tutor_id'])
        )
        tutor = tutor.scalar_one_or_none()
        
        if not child or not tutor:
            await callback_query.message.edit_text(
                "Ошибка: не удалось получить данные. Попробуйте начать сначала.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Создаем клавиатуру с предметами
        keyboard = get_subjects_keyboard(tutor.subjects)
        
        # Формируем текст с доступными типами занятий для каждого предмета
        subjects_info = "\n".join(
            f"📚 {subj['name']}: " + 
            ", ".join(filter(None, [
                "стандартное занятие" if subj.get('is_standard') else None,
                "подготовка к экзамену" if subj.get('is_exam') else None
            ]))
            for subj in tutor.subjects
            if subj.get('is_standard') or subj.get('is_exam')
        )
        
        # Отправляем сообщение с выбором предмета
        message_text = (
            f"Выберите предмет для занятия:\n"
            f"👤 Ученик: {child.name}\n"
            f"👨‍🏫 Репетитор: {tutor.name} {tutor.surname}\n\n"
            f"Доступные предметы и типы занятий:\n{subjects_info}"
        )
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard
        )
        
        # Возвращаемся к состоянию выбора предмета
        await state.set_state(BookingStates.waiting_for_subject)

async def cancel_booking(callback_query: types.CallbackQuery, state: FSMContext):
    """Отменяет процесс бронирования"""
    await state.clear()
    await callback_query.message.edit_text(
        "Бронирование отменено.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
        ])
    )

async def process_calendar_navigation(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает навигацию по календарю"""
    year, month = map(int, callback_query.data.split('_')[1:])
    state_data = await state.get_data()
    
    async with async_session_maker() as session:
        tutor = await session.execute(
            select(Tutor).where(Tutor.id == state_data['tutor_id'])
        )
        tutor = tutor.scalar_one_or_none()
        
        if not tutor:
            await callback_query.message.edit_text(
                "Ошибка: не удалось получить данные репетитора.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Получаем первый и последний день месяца
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Получаем доступные даты для выбранного месяца
        available_dates = await get_available_dates(
            tutor.schedule,
            tutor.id,
            state_data['lesson_duration'],
            start_date,
            end_date
        )
        
        # Создаем клавиатуру-календарь
        keyboard = create_calendar_keyboard(year, month, available_dates)
        
        # Обновляем сообщение с календарем
        await callback_query.message.edit_reply_markup(reply_markup=keyboard)

async def process_date_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор даты"""
    selected_date = datetime.strptime(
        callback_query.data.split('_')[-1],
        '%Y-%m-%d'
    ).date()
    
    state_data = await state.get_data()
    
    async with async_session_maker() as session:
        # Получаем данные о репетиторе
        tutor = await session.execute(
            select(Tutor).where(Tutor.id == state_data['tutor_id'])
        )
        tutor = tutor.scalar_one_or_none()
        
        if not tutor:
            await callback_query.message.edit_text(
                "Ошибка: не удалось получить данные репетитора.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Получаем существующие записи на эту дату
        existing_bookings = await session.execute(
            select(Booking)
            .where(
                Booking.tutor_id == tutor.id,
                Booking.date == selected_date,
                Booking.status == 'active'
            )
        )
        existing_bookings = existing_bookings.scalars().all()
        
        # Получаем доступные временные слоты
        available_slots = await calculate_available_slots(
            tutor.schedule,
            existing_bookings,
            state_data['lesson_duration'],
            selected_date
        )
        
        if not available_slots:
            await callback_query.message.edit_text(
                "К сожалению, на выбранную дату нет свободных слотов. Пожалуйста, выберите другую дату.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад к календарю", callback_data="back_to_calendar")],
                    [InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_booking")]
                ])
            )
            return
        
        # Сохраняем выбранную дату
        await state.update_data(selected_date=selected_date)
        
        # Создаем клавиатуру с доступными временными слотами
        keyboard = get_time_slots_keyboard(available_slots)
        
        # Получаем данные о ребенке для сообщения
        child = await session.execute(
            select(Child).where(Child.id == state_data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        # Формируем сообщение
        message_text = (
            f"Выберите удобное время занятия:\n\n"
            f"👤 Ученик: {child.name}\n"
            f"👨‍🏫 Репетитор: {tutor.name} {tutor.surname}\n"
            f"📚 Предмет: {state_data['subject_name']}\n"
            f"📝 Тип занятия: {'Подготовка к экзамену' if state_data['lesson_type'] == 'exam' else 'Стандартное занятие'}\n"
            f"📅 Дата: {selected_date.strftime('%d.%m.%Y')}\n"
            f"⏱ Длительность: {state_data['lesson_duration']} минут\n"
            f"💰 Стоимость: {state_data['price']} ₽\n\n"
            f"Доступное время:"
        )
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard
        )
        
        # Переходим к следующему состоянию
        await state.set_state(BookingStates.waiting_for_time)

async def process_time_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор времени и показывает подтверждение бронирования"""
    # Получаем выбранное время из callback_data
    start_time_str, end_time_str = callback_query.data.split('_')[2:]
    
    # Преобразуем строки времени в объекты time
    start_time = datetime.strptime(start_time_str, '%H:%M').time()
    end_time = datetime.strptime(end_time_str, '%H:%M').time()
    
    # Получаем сохраненные данные
    state_data = await state.get_data()
    
    async with async_session_maker() as session:
        # Получаем данные о ребенке, репетиторе и предмете
        child = await session.execute(
            select(Child).where(Child.id == state_data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        tutor = await session.execute(
            select(Tutor).where(Tutor.id == state_data['tutor_id'])
        )
        tutor = tutor.scalar_one_or_none()
        
        if not child or not tutor:
            await callback_query.message.edit_text(
                "Ошибка: не удалось получить данные. Попробуйте начать сначала.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            await state.clear()
            return
        
        # Сохраняем выбранное время
        await state.update_data(
            start_time=start_time_str,
            end_time=end_time_str
        )
        
        # Формируем сообщение с подтверждением
        message_text = (
            "📝 Подтвердите запись на занятие:\n\n"
            f"👤 Ученик: {child.name}\n"
            f"👨‍🏫 Репетитор: {tutor.name} {tutor.surname}\n"
            f"📚 Предмет: {state_data['subject_name']}\n"
            f"📝 Тип занятия: {'Подготовка к экзамену' if state_data['lesson_type'] == 'exam' else 'Стандартное занятие'}\n"
            f"📅 Дата: {state_data['selected_date'].strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {start_time_str} - {end_time_str}\n"
            f"⏱ Длительность: {state_data['lesson_duration']} минут\n"
            f"💰 Стоимость: {state_data['price']} ₽\n\n"
            "Пожалуйста, проверьте все данные и подтвердите запись."
        )
        
        # Создаем клавиатуру для подтверждения
        keyboard = get_booking_confirmation_keyboard()
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard
        )
        
        # Переходим к состоянию подтверждения
        await state.set_state(BookingStates.confirmation)

async def confirm_booking(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтверждает бронирование и создает запись в базе данных"""
    state_data = await state.get_data()
    
    async with async_session_maker() as session:
        try:
            # Создаем новую запись
            booking = Booking(
                parent_id=state_data['parent_id'],
                child_id=state_data['child_id'],
                tutor_id=state_data['tutor_id'],
                subject_name=state_data['subject_name'],
                lesson_type=state_data['lesson_type'],
                date=state_data['selected_date'],
                start_time=datetime.strptime(state_data['start_time'], '%H:%M').time(),
                end_time=datetime.strptime(state_data['end_time'], '%H:%M').time(),
                price=state_data['price'],
                status='active',
                created_at=datetime.now()
            )
            
            session.add(booking)
            await session.commit()
            
            # Отправляем сообщение об успешном бронировании
            await callback_query.message.edit_text(
                "✅ Занятие успешно забронировано!\n\n"
                "Вы можете просмотреть все ваши записи в разделе 'Мои записи'.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_bookings")],
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            
        except Exception as e:
            print(f"Error creating booking: {str(e)}")
            await callback_query.message.edit_text(
                "❌ Произошла ошибка при создании записи. Пожалуйста, попробуйте снова.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
        
        finally:
            # Очищаем состояние
            await state.clear()

def get_booking_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для подтверждения бронирования"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="confirm_booking")],
        [InlineKeyboardButton(text="◀️ Назад к выбору времени", callback_data="back_to_time_selection")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")]
    ])

async def cancel_existing_booking(callback_query: types.CallbackQuery):
    """Обрабатывает отмену существующей записи"""
    booking_id = int(callback_query.data.split('_')[-1])
    
    async with async_session_maker() as session:
        # Получаем данные о родителе
        parent = await session.execute(
            select(Parent).where(Parent.telegram_id == callback_query.from_user.id)
        )
        parent = parent.scalar_one_or_none()
        
        if not parent:
            await callback_query.message.edit_text(
                "❌ Ошибка: не удалось найти ваши данные.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return
        
        # Получаем запись
        booking = await session.execute(
            select(Booking)
            .options(
                selectinload(Booking.child),
                selectinload(Booking.tutor)
            )
            .where(
                Booking.id == booking_id,
                Booking.status == 'active'
            )
        )
        booking = booking.scalar_one_or_none()
        
        if not booking:
            await callback_query.message.edit_text(
                "❌ Запись не найдена или уже была отменена.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_bookings")],
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return
        
        # Проверяем, что запись принадлежит этому родителю
        if booking.parent_id != parent.id:
            await callback_query.message.edit_text(
                "❌ У вас нет прав на отмену этой записи.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return
        
        # Формируем сообщение с подтверждением отмены
        message_text = (
            "❗️ Вы действительно хотите отменить запись?\n\n"
            f"👤 Ученик: {booking.child.name}\n"
            f"👨‍🏫 Репетитор: {booking.tutor.name} {booking.tutor.surname}\n"
            f"📚 Предмет: {booking.subject_name}\n"
            f"📝 Тип занятия: {'Подготовка к экзамену' if booking.lesson_type == 'exam' else 'Стандартное занятие'}\n"
            f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
            f"💰 Стоимость: {booking.price} ₽"
        )
        
        # Создаем клавиатуру для подтверждения отмены
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="❌ Да, отменить запись",
                callback_data=f"confirm_cancel_booking_{booking_id}"
            )],
            [InlineKeyboardButton(
                text="◀️ Нет, вернуться к списку записей",
                callback_data="my_bookings"
            )]
        ])
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard
        )

async def confirm_cancel_booking(callback_query: types.CallbackQuery):
    """Подтверждает отмену записи"""
    booking_id = int(callback_query.data.split('_')[-1])
    
    async with async_session_maker() as session:
        try:
            # Получаем данные о родителе
            parent = await session.execute(
                select(Parent).where(Parent.telegram_id == callback_query.from_user.id)
            )
            parent = parent.scalar_one_or_none()
            
            if not parent:
                await callback_query.message.edit_text(
                    "❌ Ошибка: не удалось найти ваши данные.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                    ])
                )
                return
            
            # Получаем и обновляем запись
            booking = await session.execute(
                select(Booking)
                .where(
                    Booking.id == booking_id,
                    Booking.status == 'active'
                )
            )
            booking = booking.scalar_one_or_none()
            
            if not booking:
                await callback_query.message.edit_text(
                    "❌ Запись не найдена или уже была отменена.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_bookings")],
                        [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                    ])
                )
                return
            
            # Проверяем, что запись принадлежит этому родителю
            if booking.parent_id != parent.id:
                await callback_query.message.edit_text(
                    "❌ У вас нет прав на отмену этой записи.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                    ])
                )
                return
            
            # Обновляем статус записи
            booking.status = 'cancelled'
            await session.commit()
            
            # Отправляем сообщение об успешной отмене
            await callback_query.message.edit_text(
                "✅ Запись успешно отменена.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Мои записи", callback_data="my_bookings")],
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            
        except Exception as e:
            print(f"Error cancelling booking: {str(e)}")
            await callback_query.message.edit_text(
                "❌ Произошла ошибка при отмене записи. Пожалуйста, попробуйте снова.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )

def register_booking_handlers(dp):
    """Регистрирует обработчики для процесса бронирования"""
    dp.callback_query.register(show_bookings, lambda c: c.data == "my_bookings")
    dp.callback_query.register(start_booking, lambda c: c.data == "start_booking")
    dp.callback_query.register(process_child_selection, lambda c: c.data.startswith("book_child_"))
    dp.callback_query.register(process_tutor_selection, lambda c: c.data.startswith("book_tutor_"))
    dp.callback_query.register(process_subject_selection, lambda c: c.data.startswith("book_subject_"))
    dp.callback_query.register(process_lesson_type_selection, lambda c: c.data.startswith("book_type_"))
    dp.callback_query.register(process_calendar_navigation, lambda c: c.data.startswith("calendar_"))
    dp.callback_query.register(process_date_selection, lambda c: c.data.startswith("book_date_"))
    dp.callback_query.register(process_time_selection, lambda c: c.data.startswith("book_time_"))
    dp.callback_query.register(confirm_booking, lambda c: c.data == "confirm_booking")
    dp.callback_query.register(cancel_existing_booking, lambda c: c.data.startswith("cancel_booking_"))
    dp.callback_query.register(confirm_cancel_booking, lambda c: c.data.startswith("confirm_cancel_booking_"))
    dp.callback_query.register(back_to_child_selection, lambda c: c.data == "back_to_child_selection")
    dp.callback_query.register(back_to_tutor_selection, lambda c: c.data == "back_to_tutor_selection")
    dp.callback_query.register(back_to_subject_selection, lambda c: c.data == "back_to_subject_selection")
    dp.callback_query.register(cancel_booking, lambda c: c.data == "cancel_booking") 