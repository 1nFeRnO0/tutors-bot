from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from common.database import Parent, Tutor, FavoriteTutor, async_session_maker
from parent_bot.keyboards import get_tutors_list_keyboard, get_confirm_delete_tutor_keyboard

class TutorManagement(StatesGroup):
    """Состояния управления репетиторами"""
    waiting_for_tutor_id = State()

async def show_tutors_list(callback_query: types.CallbackQuery):
    """Показывает список репетиторов родителя"""
    async with async_session_maker() as session:
        async with session.begin():
            parent = await session.execute(
                select(Parent)
                .options(selectinload(Parent.favorite_tutors).selectinload(FavoriteTutor.tutor))
                .where(Parent.telegram_id == callback_query.from_user.id)
            )
            parent = parent.scalar_one_or_none()
            
            if not parent:
                await callback_query.answer("❌ Профиль не найден!")
                return
            
            tutors = [ft.tutor for ft in parent.favorite_tutors]
            
            if not tutors:
                text = "У вас пока нет добавленных репетиторов. Нажмите кнопку ниже, чтобы добавить репетитора:"
            else:
                text = "Список ваших репетиторов:"
            
            await callback_query.message.edit_text(
                text,
                reply_markup=get_tutors_list_keyboard(tutors)
            )

async def start_add_tutor(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает процесс добавления репетитора"""
    await callback_query.message.edit_text(
        "Введите Telegram ID репетитора:"
    )
    await state.set_state(TutorManagement.waiting_for_tutor_id)

async def process_tutor_id(message: types.Message, state: FSMContext):
    """Обрабатывает ввод Telegram ID репетитора"""
    try:
        tutor_telegram_id = int(message.text)
    except ValueError:
        await message.answer(
            "❌ Некорректный формат ID. Пожалуйста, введите числовой ID:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Отмена", callback_data="tutors")]
            ])
        )
        return
    
    async with async_session_maker() as session:
        async with session.begin():
            # Проверяем существование репетитора
            tutor = await session.execute(
                select(Tutor).where(Tutor.telegram_id == tutor_telegram_id)
            )
            tutor = tutor.scalar_one_or_none()
            
            if not tutor:
                await message.answer(
                    "❌ Репетитор с таким ID не найден. Проверьте ID и попробуйте снова:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Отмена", callback_data="tutors")]
                    ])
                )
                return
            
            # Получаем родителя
            parent = await session.execute(
                select(Parent).where(Parent.telegram_id == message.from_user.id)
            )
            parent = parent.scalar_one_or_none()
            
            if not parent:
                await message.answer("❌ Ваш профиль не найден!")
                return
            
            # Проверяем, не добавлен ли уже этот репетитор
            existing = await session.execute(
                select(FavoriteTutor).where(
                    FavoriteTutor.parent_id == parent.id,
                    FavoriteTutor.tutor_id == tutor.id
                )
            )
            if existing.scalar_one_or_none():
                await message.answer(
                    "❌ Этот репетитор уже добавлен в ваш список!",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Вернуться к списку", callback_data="tutors")]
                    ])
                )
                return
            
            # Добавляем репетитора в избранное
            favorite = FavoriteTutor(parent_id=parent.id, tutor_id=tutor.id)
            session.add(favorite)
            
            await message.answer(
                "✅ Репетитор успешно добавлен!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Показать список репетиторов", callback_data="tutors")]
                ])
            )
            await state.clear()

async def confirm_delete_tutor(callback_query: types.CallbackQuery):
    """Запрашивает подтверждение удаления репетитора"""
    tutor_id = int(callback_query.data.split('_')[-1])  # Берем последний элемент после split
    
    async with async_session_maker() as session:
        tutor = await session.execute(
            select(Tutor).where(Tutor.id == tutor_id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if tutor:
            tutor_name = f"{tutor.name} {tutor.surname}"
            if tutor.patronymic:
                tutor_name = f"{tutor.name} {tutor.patronymic} {tutor.surname}"
            
            await callback_query.message.edit_text(
                f"Вы уверены, что хотите удалить репетитора {tutor_name} из избранного?",
                reply_markup=get_confirm_delete_tutor_keyboard(tutor_id)
            )

async def delete_tutor(callback_query: types.CallbackQuery):
    """Удаляет репетитора из избранного"""
    tutor_id = int(callback_query.data.split('_')[-1])  # Берем последний элемент после split
    
    async with async_session_maker() as session:
        async with session.begin():
            parent = await session.execute(
                select(Parent).where(Parent.telegram_id == callback_query.from_user.id)
            )
            parent = parent.scalar_one_or_none()
            
            if parent:
                favorite = await session.execute(
                    select(FavoriteTutor).where(
                        FavoriteTutor.parent_id == parent.id,
                        FavoriteTutor.tutor_id == tutor_id
                    )
                )
                favorite = favorite.scalar_one_or_none()
                
                if favorite:
                    await session.delete(favorite)
    
    await callback_query.answer("Репетитор удален из избранного")
    await show_tutors_list(callback_query)

def register_tutors_handlers(dp):
    """Регистрирует обработчики для управления репетиторами"""
    dp.callback_query.register(show_tutors_list, lambda c: c.data == "tutors")
    dp.callback_query.register(start_add_tutor, lambda c: c.data == "add_tutor")
    dp.message.register(process_tutor_id, TutorManagement.waiting_for_tutor_id)
    dp.callback_query.register(confirm_delete_tutor, lambda c: c.data.startswith("favorite_delete_tutor_"))
    dp.callback_query.register(delete_tutor, lambda c: c.data.startswith("favorite_confirm_delete_tutor_")) 