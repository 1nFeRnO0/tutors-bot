from datetime import datetime
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, joinedload

from common.database import async_session_maker, Booking, BookingStatus, Tutor
from parent_bot.main import bot as parent_bot

class BookingStates(StatesGroup):
    """Состояния для работы с записями"""
    waiting_for_rejection_reason = State()  # Ожидание причины отклонения записи

async def show_pending_bookings(callback_query: types.CallbackQuery):
    """Показывает записи, ожидающие подтверждения"""
    async with async_session_maker() as session:
        # Сначала получаем данные о репетиторе
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if not tutor:
            print(f"Tutor not found. Telegram ID: {callback_query.from_user.id}")
            await callback_query.message.edit_text(
                "❌ Ошибка: не удалось найти ваши данные.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return

        print(f"Found tutor: ID={tutor.id}, telegram_id={tutor.telegram_id}")
        
        # Получаем все ожидающие записи для репетитора
        pending_bookings = await session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.tutor_id == tutor.id,  # Используем ID из базы данных
                    Booking.status == BookingStatus.PENDING
                )
            )
            .order_by(Booking.date, Booking.start_time)
            .options(
                joinedload(Booking.child),
                joinedload(Booking.parent)
            )
        )
        pending_bookings = pending_bookings.scalars().all()
        
        print(f"Found {len(pending_bookings)} pending bookings")

        if not pending_bookings:
            await callback_query.message.edit_text(
                "У вас нет записей, ожидающих подтверждения.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return

        # Показываем первую запись
        booking = pending_bookings[0]
        total_count = len(pending_bookings)
        
        text = (
            f"📋 Записи, ожидающие подтверждения ({1}/{total_count})\n\n"
            f"📚 {booking.subject_name} ({'Подготовка к экзамену' if booking.lesson_type == 'exam' else 'Стандартное занятие'})\n"
            f"👤 Ученик: {booking.child.name} {booking.child.surname}\n"
            f"👨‍👩‍👧‍👦 Родитель: {booking.parent.name} {booking.parent.surname}\n"
            f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
            f"💰 Стоимость: {booking.price} ₽"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"approve_booking_{booking.id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_booking_{booking.id}"
                )
            ]
        ]

        if total_count > 1:
            keyboard.append([
                InlineKeyboardButton(
                    text="➡️ Следующая запись",
                    callback_data=f"next_pending_booking_1"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")
        ])

        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

async def show_next_pending_booking(callback_query: types.CallbackQuery):
    """Показывает следующую запись, ожидающую подтверждения"""
    current_index = int(callback_query.data.split('_')[-1])
    
    async with async_session_maker() as session:
        # Сначала получаем данные о репетиторе
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if not tutor:
            await callback_query.message.edit_text(
                "❌ Ошибка: не удалось найти ваши данные.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return

        pending_bookings = await session.execute(
            select(Booking)
            .where(
                and_(
                    Booking.tutor_id == tutor.id,  # Используем ID из базы данных
                    Booking.status == BookingStatus.PENDING
                )
            )
            .order_by(Booking.date, Booking.start_time)
            .options(
                joinedload(Booking.child),
                joinedload(Booking.parent)
            )
        )
        pending_bookings = pending_bookings.scalars().all()
        total_count = len(pending_bookings)

        if current_index >= total_count:
            # Если достигли конца списка, начинаем сначала
            current_index = 0

        booking = pending_bookings[current_index]
        
        text = (
            f"📋 Записи, ожидающие подтверждения ({current_index + 1}/{total_count})\n\n"
            f"📚 {booking.subject_name} ({'Подготовка к экзамену' if booking.lesson_type == 'exam' else 'Стандартное занятие'})\n"
            f"👤 Ученик: {booking.child.name} {booking.child.surname}\n"
            f"👨‍👩‍👧‍👦 Родитель: {booking.parent.name} {booking.parent.surname}\n"
            f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
            f"💰 Стоимость: {booking.price} ₽"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"approve_booking_{booking.id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_booking_{booking.id}"
                )
            ]
        ]

        if total_count > 1:
            keyboard.append([
                InlineKeyboardButton(
                    text="⬅️ Предыдущая",
                    callback_data=f"next_pending_booking_{(current_index - 1) % total_count}"
                ),
                InlineKeyboardButton(
                    text="➡️ Следующая",
                    callback_data=f"next_pending_booking_{(current_index + 1) % total_count}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")
        ])

        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

async def approve_booking(callback_query: types.CallbackQuery):
    """Подтверждает запись на занятие"""
    booking_id = int(callback_query.data.split('_')[-1])
    
    async with async_session_maker() as session:
        try:
            # Получаем данные о репетиторе
            tutor = await session.execute(
                select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
            )
            tutor = tutor.scalar_one_or_none()
            
            if not tutor:
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
                    selectinload(Booking.parent)
                )
                .where(
                    Booking.id == booking_id,
                    Booking.status == BookingStatus.PENDING
                )
            )
            booking = booking.scalar_one_or_none()
            
            if not booking:
                await callback_query.message.edit_text(
                    "❌ Запись не найдена или уже была обработана.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📋 Ожидающие записи", callback_data="tutor_pending_bookings")],
                        [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                    ])
                )
                return
            
            # Проверяем, что запись принадлежит этому репетитору
            if booking.tutor_id != tutor.id:
                await callback_query.message.edit_text(
                    "❌ У вас нет прав на подтверждение этой записи.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                    ])
                )
                return
            
            # Обновляем статус записи
            booking.status = BookingStatus.APPROVED
            booking.approved_at = datetime.utcnow()
            await session.commit()
            
            # Уведомляем родителя о подтверждении
            notification_text = (
                "✅ Репетитор подтвердил запись!\n\n"
                f"👤 Ученик: {booking.child.name} {booking.child.surname}\n"
                f"👨‍🏫 Репетитор: {tutor.name} {tutor.surname}\n"
                f"📚 Предмет: {booking.subject_name}\n"
                f"📝 Тип занятия: {'Подготовка к экзамену' if booking.lesson_type == 'exam' else 'Стандартное занятие'}\n"
                f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
                f"🕒 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
                f"💰 Стоимость: {booking.price} ₽"
            )
            
            await parent_bot.send_message(
                chat_id=booking.parent.telegram_id,
                text=notification_text
            )
            
            # Отправляем сообщение об успешном подтверждении
            await callback_query.message.edit_text(
                "✅ Запись успешно подтверждена.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Ожидающие записи", callback_data="tutor_pending_bookings")],
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            
        except Exception as e:
            print(f"Error approving booking: {str(e)}")
            await callback_query.message.edit_text(
                "❌ Произошла ошибка при подтверждении записи. Пожалуйста, попробуйте снова.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )

async def reject_booking(callback_query: types.CallbackQuery, state: FSMContext):
    """Начинает процесс отклонения записи"""
    booking_id = int(callback_query.data.split('_')[-1])
    
    async with async_session_maker() as session:
        # Получаем данные о репетиторе
        tutor = await session.execute(
            select(Tutor).where(Tutor.telegram_id == callback_query.from_user.id)
        )
        tutor = tutor.scalar_one_or_none()
        
        if not tutor:
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
                selectinload(Booking.parent)
            )
            .where(
                Booking.id == booking_id,
                Booking.status == BookingStatus.PENDING
            )
        )
        booking = booking.scalar_one_or_none()
        
        if not booking:
            await callback_query.message.edit_text(
                "❌ Запись не найдена или уже была обработана.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Ожидающие записи", callback_data="tutor_pending_bookings")],
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return
        
        # Проверяем, что запись принадлежит этому репетитору
        if booking.tutor_id != tutor.id:
            await callback_query.message.edit_text(
                "❌ У вас нет прав на отклонение этой записи.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            return
        
        # Сохраняем ID записи в состоянии
        await state.set_state(BookingStates.waiting_for_rejection_reason)
        await state.update_data(booking_id=booking_id)
        
        # Запрашиваем причину отклонения
        await callback_query.message.edit_text(
            "Пожалуйста, укажите причину отклонения записи.\n\n"
            "Например:\n"
            "- Я занят в это время\n"
            "- У меня уже есть запись на это время\n"
            "- Я не работаю в это время\n"
            "- Другая причина\n\n"
            "✍️ Отправьте сообщение с причиной:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_rejection")]
            ])
        )

async def process_rejection_reason(message: types.Message, state: FSMContext):
    """Обрабатывает причину отклонения записи"""
    state_data = await state.get_data()
    booking_id = state_data.get('booking_id')
    
    if not booking_id:
        await message.answer(
            "❌ Произошла ошибка. Пожалуйста, попробуйте снова.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
            ])
        )
        await state.clear()
        return
    
    async with async_session_maker() as session:
        try:
            # Получаем запись
            booking = await session.execute(
                select(Booking)
                .options(
                    selectinload(Booking.child),
                    selectinload(Booking.parent),
                    selectinload(Booking.tutor)
                )
                .where(
                    Booking.id == booking_id,
                    Booking.status == BookingStatus.PENDING
                )
            )
            booking = booking.scalar_one_or_none()
            
            if not booking:
                await message.answer(
                    "❌ Запись не найдена или уже была обработана.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📋 Ожидающие записи", callback_data="tutor_pending_bookings")],
                        [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                    ])
                )
                await state.clear()
                return
            
            # Обновляем статус записи
            booking.status = BookingStatus.REJECTED
            booking.rejection_reason = message.text
            await session.commit()
            
            # Уведомляем родителя об отклонении
            notification_text = (
                "❌ Репетитор отклонил запись\n\n"
                f"👤 Ученик: {booking.child.name} {booking.child.surname}\n"
                f"👨‍🏫 Репетитор: {booking.tutor.name} {booking.tutor.surname}\n"
                f"📚 Предмет: {booking.subject_name}\n"
                f"📝 Тип занятия: {'Подготовка к экзамену' if booking.lesson_type == 'exam' else 'Стандартное занятие'}\n"
                f"📅 Дата: {booking.date.strftime('%d.%m.%Y')}\n"
                f"🕒 Время: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
                f"❗️ Причина: {booking.rejection_reason}"
            )
            
            await parent_bot.send_message(
                chat_id=booking.parent.telegram_id,
                text=notification_text
            )
            
            # Отправляем сообщение об успешном отклонении
            await message.answer(
                "✅ Запись успешно отклонена.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Ожидающие записи", callback_data="tutor_pending_bookings")],
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
            
        except Exception as e:
            print(f"Error rejecting booking: {str(e)}")
            await message.answer(
                "❌ Произошла ошибка при отклонении записи. Пожалуйста, попробуйте снова.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
                ])
            )
        
        finally:
            await state.clear()

async def cancel_rejection(callback_query: types.CallbackQuery, state: FSMContext):
    """Отменяет процесс отклонения записи"""
    await state.clear()
    await callback_query.message.edit_text(
        "❌ Отклонение записи отменено.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Ожидающие записи", callback_data="tutor_pending_bookings")],
            [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="back_to_main")]
        ])
    )

def register_booking_handlers(dp):
    """Регистрирует обработчики для работы с записями"""
    dp.callback_query.register(show_pending_bookings, lambda c: c.data == "tutor_pending_bookings")
    dp.callback_query.register(show_next_pending_booking, lambda c: c.data.startswith("next_pending_booking_"))
    dp.callback_query.register(approve_booking, lambda c: c.data.startswith("approve_booking_"))
    dp.callback_query.register(reject_booking, lambda c: c.data.startswith("reject_booking_"))
    dp.callback_query.register(cancel_rejection, lambda c: c.data == "cancel_rejection", BookingStates.waiting_for_rejection_reason)
    dp.message.register(process_rejection_reason, BookingStates.waiting_for_rejection_reason) 