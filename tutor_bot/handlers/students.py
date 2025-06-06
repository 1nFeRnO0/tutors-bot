from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, distinct
from sqlalchemy.orm import joinedload, contains_eager

from common.database import async_session_maker, Booking, Child, BookingStatus, Tutor

async def show_my_students(callback_query: types.CallbackQuery):
    """Показывает список учеников, которые записывались к репетитору"""
    async with async_session_maker() as session:
        # Получаем уникальных учеников, у которых были записи к этому репетитору
        query = (
            select(Child)
            .join(Child.bookings)
            .join(Booking.tutor)
            .where(Tutor.telegram_id == callback_query.from_user.id)
            .options(contains_eager(Child.bookings))
            .distinct()
        )
        
        result = await session.execute(query)
        students = result.unique().scalars().all()

        if not students:
            await callback_query.message.edit_text(
                "У вас пока нет учеников.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return

        # Создаем клавиатуру со списком учеников
        keyboard = []
        for student in students:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{student.name} {student.surname}",
                    callback_data=f"show_student_{student.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")])

        await callback_query.message.edit_text(
            "Выберите ученика, чтобы посмотреть информацию о нем:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

async def show_student_info(callback_query: types.CallbackQuery):
    """Показывает подробную информацию об ученике"""
    student_id = int(callback_query.data.split('_')[2])

    async with async_session_maker() as session:
        # Получаем данные об ученике и его записях к текущему репетитору
        query = (
            select(Child)
            .options(joinedload(Child.bookings).joinedload(Booking.tutor))
            .where(Child.id == student_id)
        )
        
        result = await session.execute(query)
        student = result.unique().scalar_one_or_none()

        if not student:
            await callback_query.message.edit_text(
                "❌ Ученик не найден.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться к списку учеников", callback_data="my_students")]
                ])
            )
            return

        # Фильтруем записи только для текущего репетитора
        tutor_bookings = [
            booking for booking in student.bookings 
            if booking.tutor.telegram_id == callback_query.from_user.id
        ]

        # Подсчитываем статистику по записям
        total_bookings = len(tutor_bookings)
        completed_bookings = sum(1 for b in tutor_bookings if b.status == BookingStatus.APPROVED)
        upcoming_bookings = 0  # TODO: Add logic for upcoming bookings

        # Формируем текст с информацией об ученике
        text = (
            f"👤 Ученик: {student.name} {student.surname}\n"
            f"{'🧑' if student.gender.value == 'male' else '👧'} Пол: {'Мужской' if student.gender.value == 'male' else 'Женский'}\n"
            f"📚 Класс: {student.grade}\n"
            f"📖 Учебник: {student.textbook_info or 'Не указан'}\n\n"
            f"📊 Статистика занятий с вами:\n"
            f"• Всего занятий: {total_bookings}\n"
            f"• Подтверждено: {completed_bookings}\n"
            f"• Предстоит: {upcoming_bookings}"
        )

        keyboard = [
            [InlineKeyboardButton(text="◀️ Вернуться к списку учеников", callback_data="my_students")],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="back_to_main")]
        ]

        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

def register_students_handlers(dp):
    """Регистрирует обработчики для работы со списком учеников"""
    dp.callback_query.register(show_my_students, lambda c: c.data == "my_students")
    dp.callback_query.register(show_student_info, lambda c: c.data.startswith("show_student_")) 