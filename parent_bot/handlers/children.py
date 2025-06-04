from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from contextlib import asynccontextmanager
from sqlalchemy.orm import selectinload
import asyncio

from common.database import Parent, Child, Gender, async_session_maker
from parent_bot.keyboards import (
    get_children_list_keyboard, get_gender_keyboard, 
    get_grade_keyboard, get_child_edit_keyboard,
    get_fio_edit_keyboard
)

class AddChildStates(StatesGroup):
    """Состояния для добавления нового ребенка"""
    waiting_for_name = State()
    waiting_for_surname = State()
    waiting_for_patronymic = State()
    waiting_for_gender = State()
    waiting_for_grade = State()
    waiting_for_textbook = State()

class EditChildStates(StatesGroup):
    """Состояния для редактирования данных ребенка"""
    main_menu = State()  # Основное меню редактирования
    fio_menu = State()   # Меню редактирования ФИО
    editing_name = State()
    editing_surname = State()
    editing_patronymic = State()
    editing_gender = State()
    editing_grade = State()
    editing_textbook = State()
    editing_textbook_input = State()

# === Handlers for adding a new child ===

async def start_add_child(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает процесс добавления ребенка"""
    await callback_query.message.edit_text("Введите имя ребенка:")
    await state.set_state(AddChildStates.waiting_for_name)

async def process_add_name(message: types.Message, state: FSMContext):
    """Обработка ввода имени при добавлении"""
    await state.update_data(name=message.text)
    await message.answer("Введите фамилию ребенка:")
    await state.set_state(AddChildStates.waiting_for_surname)

async def process_add_surname(message: types.Message, state: FSMContext):
    """Обработка ввода фамилии при добавлении"""
    await state.update_data(surname=message.text)
    await message.answer(
        "Введите отчество ребенка (или нажмите кнопку пропустить):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="skip_add_patronymic")]
        ])
    )
    await state.set_state(AddChildStates.waiting_for_patronymic)

async def process_add_patronymic(message: types.Message, state: FSMContext):
    """Обработка ввода отчества при добавлении"""
    await state.update_data(patronymic=message.text)
    await message.answer(
        "Выберите пол ребенка:",
        reply_markup=get_gender_keyboard()
    )
    await state.set_state(AddChildStates.waiting_for_gender)

async def skip_add_patronymic(callback_query: types.CallbackQuery, state: FSMContext):
    """Пропуск ввода отчества при добавлении"""
    await state.update_data(patronymic=None)
    await callback_query.message.edit_text(
        "Выберите пол ребенка:",
        reply_markup=get_gender_keyboard()
    )
    await state.set_state(AddChildStates.waiting_for_gender)

async def process_add_gender(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора пола при добавлении"""
    gender = Gender.MALE if callback_query.data == "add_gender_M" else Gender.FEMALE
    await state.update_data(gender=gender)
    
    await callback_query.message.edit_text(
        "Выберите класс обучения:",
        reply_markup=get_grade_keyboard()
    )
    await state.set_state(AddChildStates.waiting_for_grade)

async def process_add_grade(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора класса при добавлении"""
    grade = int(callback_query.data.split('_')[2])
    await state.update_data(grade=grade)
    
    await callback_query.message.edit_text(
        "Введите информацию об учебнике (автор, издательство, год издания):"
    )
    await state.set_state(AddChildStates.waiting_for_textbook)

async def process_add_textbook(message: types.Message, state: FSMContext):
    """Завершает процесс добавления ребенка"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        async with session.begin():
            parent = await session.execute(
                select(Parent).where(Parent.telegram_id == message.from_user.id)
            )
            parent = parent.scalar_one_or_none()
            
            if parent:
                child = Child(
                    parent_id=parent.id,
                    name=data['name'],
                    surname=data['surname'],
                    patronymic=data.get('patronymic'),
                    gender=data['gender'],
                    grade=data['grade'],
                    textbook_info=message.text
                )
                session.add(child)
    
    await message.answer(
        "✅ Ребенок успешно добавлен!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Показать список детей", callback_data="show_children")]
        ])
    )
    await state.clear()

# === Handlers for editing child information ===

async def start_edit_child(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает процесс редактирования данных ребенка"""
    child_id = int(callback_query.data.split('_')[2])
    
    async with async_session_maker() as session:
        child = await session.execute(
            select(Child).where(Child.id == child_id)
        )
        child = child.scalar_one_or_none()
        
        if child:
            await state.update_data(child_id=child_id)
            textbook_info = child.textbook_info or "Не указано"
            await callback_query.message.edit_text(
                f"Редактирование данных ребенка:\n\n"
                f"📚 Учебник: {textbook_info}",
                reply_markup=get_child_edit_keyboard(child)
            )
            await state.set_state(EditChildStates.main_menu)

async def edit_fio(callback_query: types.CallbackQuery, state: FSMContext):
    """Показывает меню редактирования ФИО"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        child = await session.execute(
            select(Child).where(Child.id == data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        if child:
            await callback_query.message.edit_text(
                "Редактирование ФИО:",
                reply_markup=get_fio_edit_keyboard(child)
            )
            await state.set_state(EditChildStates.fio_menu)

async def edit_back(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат в основное меню редактирования"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        child = await session.execute(
            select(Child).where(Child.id == data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        if child:
            textbook_info = child.textbook_info or "Не указано"
            await callback_query.message.edit_text(
                f"Редактирование данных ребенка:\n\n"
                f"📚 Учебник: {textbook_info}",
                reply_markup=get_child_edit_keyboard(child)
            )
            await state.set_state(EditChildStates.main_menu)

async def edit_name(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает редактирование имени"""
    print('я здесь')
    await callback_query.message.edit_text("Введите новое имя ребенка:")
    await state.set_state(EditChildStates.editing_name)

async def edit_surname(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает редактирование фамилии"""
    await callback_query.message.edit_text("Введите новую фамилию ребенка:")
    await state.set_state(EditChildStates.editing_surname)

async def edit_patronymic(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает редактирование отчества"""
    await callback_query.message.edit_text(
        "Введите новое отчество ребенка (или нажмите кнопку пропустить):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="skip_edit_patronymic")]
        ])
    )
    await state.set_state(EditChildStates.editing_patronymic)

async def process_edit_name(message: types.Message, state: FSMContext):
    """Обрабатывает ввод нового имени"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        async with session.begin():
            child = await session.execute(
                select(Child).where(Child.id == data['child_id'])
            )
            child = child.scalar_one_or_none()
            
            if child:
                child.name = message.text
                await message.answer(
                    "Редактирование ФИО:",
                    reply_markup=get_fio_edit_keyboard(child)
                )
                await state.set_state(EditChildStates.fio_menu)

async def process_edit_surname(message: types.Message, state: FSMContext):
    """Обрабатывает ввод новой фамилии"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        async with session.begin():
            child = await session.execute(
                select(Child).where(Child.id == data['child_id'])
            )
            child = child.scalar_one_or_none()
            
            if child:
                child.surname = message.text
                await message.answer(
                    "Редактирование ФИО:",
                    reply_markup=get_fio_edit_keyboard(child)
                )
                await state.set_state(EditChildStates.fio_menu)

async def process_edit_patronymic(message: types.Message, state: FSMContext):
    """Обрабатывает ввод нового отчества"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        async with session.begin():
            child = await session.execute(
                select(Child).where(Child.id == data['child_id'])
            )
            child = child.scalar_one_or_none()
            
            if child:
                child.patronymic = message.text
                await message.answer(
                    "Редактирование ФИО:",
                    reply_markup=get_fio_edit_keyboard(child)
                )
                await state.set_state(EditChildStates.fio_menu)

async def skip_edit_patronymic(callback_query: types.CallbackQuery, state: FSMContext):
    """Пропуск ввода отчества при редактировании"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        async with session.begin():
            child = await session.execute(
                select(Child).where(Child.id == data['child_id'])
            )
            child = child.scalar_one_or_none()
            
            if child:
                child.patronymic = None
                await callback_query.message.edit_text(
                    "Редактирование ФИО:",
                    reply_markup=get_fio_edit_keyboard(child)
                )
                await state.set_state(EditChildStates.fio_menu)

async def edit_grade(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает редактирование класса"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        child = await session.execute(
            select(Child).where(Child.id == data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        if child:
            await callback_query.message.edit_text(
                "Выберите новый класс:",
                reply_markup=get_grade_keyboard(selected_grade=child.grade, is_edit=True)
            )
            await state.set_state(EditChildStates.editing_grade)

async def process_edit_grade(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор нового класса"""
    data = await state.get_data()
    grade = int(callback_query.data.split('_')[2])
    
    async with async_session_maker() as session:
        async with session.begin():
            child = await session.execute(
                select(Child).where(Child.id == data['child_id'])
            )
            child = child.scalar_one_or_none()
            
            if child:
                child.grade = grade
                textbook_info = child.textbook_info or "Не указано"
                await callback_query.message.edit_text(
                    f"Редактирование данных ребенка:\n\n"
                    f"📚 Учебник: {textbook_info}",
                    reply_markup=get_child_edit_keyboard(child)
                )
                await state.set_state(EditChildStates.main_menu)

async def edit_textbook(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает редактирование информации об учебнике"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        child = await session.execute(
            select(Child).where(Child.id == data['child_id'])
        )
        child = child.scalar_one_or_none()
        
        if child:
            current_textbook = child.textbook_info or "Не указано"
            await callback_query.message.edit_text(
                f"Текущая информация об учебнике:\n{current_textbook}\n\n"
                "Введите новую информацию об учебнике:"
            )
            await state.set_state(EditChildStates.editing_textbook_input)

async def process_edit_textbook(message: types.Message, state: FSMContext):
    """Обрабатывает ввод новой информации об учебнике"""
    data = await state.get_data()
    
    async with async_session_maker() as session:
        async with session.begin():
            child = await session.execute(
                select(Child).where(Child.id == data['child_id'])
            )
            child = child.scalar_one_or_none()
            
            if child:
                child.textbook_info = message.text
                textbook_info = child.textbook_info or "Не указано"
                await message.answer(
                    f"Редактирование данных ребенка:\n\n"
                    f"📚 Учебник: {textbook_info}",
                    reply_markup=get_child_edit_keyboard(child)
                )
                await state.set_state(EditChildStates.main_menu)

# === Delete child handlers ===

async def confirm_delete_child(callback_query: types.CallbackQuery):
    """Запрашивает подтверждение удаления ребенка"""
    child_id = int(callback_query.data.split('_')[2])
    
    async with async_session_maker() as session:
        child = await session.execute(
            select(Child).where(Child.id == child_id)
        )
        child = child.scalar_one_or_none()
        
        if child:
            child_name = f"{child.name} {child.surname}"
            if child.patronymic:
                child_name = f"{child.name} {child.patronymic} {child.surname}"
            
            await callback_query.message.edit_text(
                f"Вы уверены, что хотите удалить {child_name}?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Да", callback_data=f"confirm_delete_{child_id}"),
                        InlineKeyboardButton(text="Нет", callback_data="show_children")
                    ]
                ])
            )

async def delete_child(callback_query: types.CallbackQuery):
    """Удаляет ребенка"""
    child_id = int(callback_query.data.split('_')[2])
    
    async with async_session_maker() as session:
        async with session.begin():
            child = await session.execute(
                select(Child).where(Child.id == child_id)
            )
            child = child.scalar_one_or_none()
            
            if child:
                await session.delete(child)
    
    await callback_query.answer("Ребенок удален")
    await show_children_list(callback_query)

async def show_children_list(callback_query: types.CallbackQuery):
    """Показывает список детей родителя"""
    async with async_session_maker() as session:
        async with session.begin():
            parent = await session.execute(
                select(Parent).options(selectinload(Parent.children)).where(Parent.telegram_id == callback_query.from_user.id)
            )
            parent = parent.scalar_one_or_none()
            
            if not parent:
                await callback_query.answer("❌ Профиль не найден!")
                return
            
            if not parent.children:
                text = "У вас пока нет добавленных детей. Нажмите кнопку ниже, чтобы добавить ребенка:"
            else:
                text = "Список ваших детей:"
            
            await callback_query.message.edit_text(
                text,
                reply_markup=get_children_list_keyboard(parent.children)
            )

def register_children_handlers(dp):
    """Регистрирует обработчики для управления детьми"""
    # Просмотр списка детей
    dp.callback_query.register(show_children_list, lambda c: c.data == "children")
    dp.callback_query.register(show_children_list, lambda c: c.data == "show_children")
    
    # Добавление ребенка
    dp.callback_query.register(start_add_child, lambda c: c.data == "add_child")
    dp.message.register(process_add_name, AddChildStates.waiting_for_name)
    dp.message.register(process_add_surname, AddChildStates.waiting_for_surname)
    dp.message.register(process_add_patronymic, AddChildStates.waiting_for_patronymic)
    dp.callback_query.register(skip_add_patronymic, lambda c: c.data == "skip_add_patronymic")
    dp.callback_query.register(process_add_gender, lambda c: c.data.startswith("add_gender_"))
    dp.callback_query.register(process_add_grade, lambda c: c.data.startswith("add_grade_"))
    dp.message.register(process_add_textbook, AddChildStates.waiting_for_textbook)
    
    # Редактирование ребенка
    dp.callback_query.register(start_edit_child, lambda c: c.data.startswith("edit_child_"))
    dp.callback_query.register(edit_fio, lambda c: c.data == "edit_fio")
    dp.callback_query.register(edit_back, lambda c: c.data == "edit_back")
    dp.callback_query.register(edit_name, lambda c: c.data == "child_edit_name")
    dp.callback_query.register(edit_surname, lambda c: c.data == "child_edit_surname")
    dp.callback_query.register(edit_patronymic, lambda c: c.data == "child_edit_patronymic")
    dp.callback_query.register(edit_grade, lambda c: c.data == "edit_grade")
    dp.callback_query.register(edit_textbook, lambda c: c.data == "edit_textbook")
    dp.message.register(process_edit_name, EditChildStates.editing_name)
    dp.message.register(process_edit_surname, EditChildStates.editing_surname)
    dp.message.register(process_edit_patronymic, EditChildStates.editing_patronymic)
    dp.callback_query.register(skip_edit_patronymic, lambda c: c.data == "skip_edit_patronymic")
    dp.callback_query.register(process_edit_grade, lambda c: c.data.startswith("edit_grade_"))
    dp.message.register(process_edit_textbook, EditChildStates.editing_textbook_input)
    
    # Удаление ребенка
    dp.callback_query.register(confirm_delete_child, lambda c: c.data.startswith("delete_child_"))
    dp.callback_query.register(delete_child, lambda c: c.data.startswith("confirm_delete_")) 