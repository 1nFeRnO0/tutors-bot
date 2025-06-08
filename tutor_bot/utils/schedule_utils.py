from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.database import Booking, BookingStatus, Tutor

# Русские названия месяцев в родительном падеже (для дат)
MONTHS_RU_GENITIVE = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря"
}

# Русские названия месяцев в именительном падеже (для заголовков)
MONTHS_RU_NOMINATIVE = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь"
}

def get_date_range(period: str) -> tuple[date, date]:
    """Возвращает диапазон дат для заданного периода"""
    today = date.today()
    
    if period == "today":
        start_date = today
        end_date = today + timedelta(days=1)
    elif period == "tomorrow":
        start_date = today + timedelta(days=1)
        end_date = today + timedelta(days=2)
    elif period == "week":
        # Начало текущей недели (понедельник)
        start_date = today - timedelta(days=today.weekday())
        # Конец недели (воскресенье)
        end_date = start_date + timedelta(days=7)
    else:  # month
        # Начало текущего месяца
        start_date = today.replace(day=1)
        # Начало следующего месяца
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1)
    
    return start_date, end_date

async def get_bookings_for_period(
    session: AsyncSession,
    telegram_id: int,
    period: str
) -> List[Booking]:
    """Получает записи для заданного периода"""
    # Сначала получаем репетитора по telegram_id
    tutor = await session.execute(
        select(Tutor).where(Tutor.telegram_id == telegram_id)
    )
    tutor = tutor.scalar_one_or_none()
    
    if not tutor:
        print(f"Tutor not found for telegram_id: {telegram_id}")
        return []
    
    start_date, end_date = get_date_range(period)
    
    query = select(Booking).options(
        selectinload(Booking.child),
        selectinload(Booking.tutor)
    ).where(
        Booking.tutor_id == tutor.id,
        Booking.date >= start_date,
        Booking.date < end_date,
        Booking.status.in_([BookingStatus.APPROVED, BookingStatus.PENDING])
    ).order_by(Booking.date, Booking.start_time)
    
    result = await session.execute(query)
    
    # from sqlalchemy.dialects import sqlite
    # compiled = query.compile(
    #     dialect=sqlite.dialect(),
    #     compile_kwargs={"literal_binds": True}
    # )

    # print(compiled)

    # print(f'DEBUG:{list(result.scalars().all())}')
    return list(result.scalars().all())

def format_booking_status(status: BookingStatus) -> str:
    """Форматирует статус записи для отображения"""
    if status == BookingStatus.APPROVED:
        return "✅ Подтверждено"
    elif status == BookingStatus.PENDING:
        return "⏳ Ожидает подтверждения"
    elif status == BookingStatus.REJECTED:
        return "❌ Отклонено"
    else:
        return "🚫 Отменено"

def format_daily_schedule(bookings: List[Booking], date_str: str) -> str:
    """Форматирует расписание на день"""
    print('DEBUG:bookings', bookings)
    if not bookings:
        return f"📅 Расписание на {date_str}\n\n🚫 Нет занятий"
    
    total_confirmed = sum(1 for b in bookings if b.status == BookingStatus.APPROVED)
    total_pending = sum(1 for b in bookings if b.status == BookingStatus.PENDING)
    total_income = sum(b.price for b in bookings if b.status == BookingStatus.APPROVED)
    
    text = [f"📅 Расписание на {date_str}\n"]
    
    for booking in bookings:
        text.extend([
            f"\n⏰ {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}",
            f"👤 {booking.child.name} {booking.child.surname} ({booking.child.grade} класс)",
            f"📚 {booking.subject_name} ({booking.lesson_type})",
            f"💰 {booking.price} руб. | {format_booking_status(booking.status)}\n"
        ])
    
    text.extend([
        "\n━━━━━━━━━━━━━━━━━━━━━━",
        f"Всего занятий: {len(bookings)}",
        f"Подтверждено: {total_confirmed} | Ожидает: {total_pending}",
        f"Доход за день: {total_income} руб."
    ])
    
    return "\n".join(text)

def format_weekly_schedule(bookings: List[Booking], week_range: str) -> str:
    """Форматирует расписание на неделю"""
    if not bookings:
        return f"📊 Расписание на неделю ({week_range})\n\n🚫 Нет занятий"
    
    # Группируем записи по дням
    bookings_by_day: Dict[date, List[Booking]] = {}
    for booking in bookings:
        if booking.date not in bookings_by_day:
            bookings_by_day[booking.date] = []
        bookings_by_day[booking.date].append(booking)
    
    # Статистика
    total_confirmed = sum(1 for b in bookings if b.status == BookingStatus.APPROVED)
    total_pending = sum(1 for b in bookings if b.status == BookingStatus.PENDING)
    total_income = sum(b.price for b in bookings if b.status == BookingStatus.APPROVED)
    
    text = [f"📊 Расписание на неделю ({week_range})\n"]
    
    # Дни недели на русском
    weekdays = ["ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА", "ВОСКРЕСЕНЬЕ"]
    
    for day_date in sorted(bookings_by_day.keys()):
        day_bookings = bookings_by_day[day_date]
        text.append(f"\n🗓 {weekdays[day_date.weekday()]}, {day_date.strftime('%d.%m')}")
        
        for booking in sorted(day_bookings, key=lambda b: b.start_time):
            text.append(
                f"⏰ {booking.start_time.strftime('%H:%M')}-{booking.end_time.strftime('%H:%M')} | "
                f"{booking.child.name} {booking.child.surname[0]}. | "
                f"{booking.subject_name}"
                + (" (экз.)" if booking.lesson_type == "exam" else "")
            )
    
    text.extend([
        "\n━━━━━━━━━━━━━━━━━━━━━━",
        f"Всего занятий на неделю: {len(bookings)}",
        f"Подтверждено: {total_confirmed} | Ожидает: {total_pending}",
        f"Доход за неделю: {total_income} руб."
    ])
    
    return "\n".join(text)

def format_date_with_month(d: date) -> str:
    """Форматирует дату с русским названием месяца в родительном падеже"""
    return f"{d.day} {MONTHS_RU_GENITIVE[d.month]}"

def format_month_title(d: date) -> str:
    """Форматирует название месяца в именительном падеже"""
    print('DEBUG:d', d.month, MONTHS_RU_NOMINATIVE[d.month])
    return f"{MONTHS_RU_NOMINATIVE[d.month]} {d.year}"

def format_monthly_schedule(bookings: List[Booking], month_str: str) -> str:
    """Форматирует расписание на месяц"""
    if not bookings:
        return f"🗓 Расписание на {month_str}\n\n🚫 Нет занятий"
    
    # Статистика
    total_confirmed = sum(1 for b in bookings if b.status == BookingStatus.APPROVED)
    total_pending = sum(1 for b in bookings if b.status == BookingStatus.PENDING)
    total_cancelled = sum(1 for b in bookings if b.status == BookingStatus.CANCELLED)
    total_income = sum(b.price for b in bookings if b.status == BookingStatus.APPROVED)
    
    # Группируем записи по неделям
    bookings_by_week: Dict[int, List[Booking]] = {}
    for booking in bookings:
        week_num = booking.date.isocalendar()[1]
        if week_num not in bookings_by_week:
            bookings_by_week[week_num] = []
        bookings_by_week[week_num].append(booking)
    
    # Группируем записи по предметам
    subjects: Dict[str, int] = {}
    for booking in bookings:
        if booking.subject_name not in subjects:
            subjects[booking.subject_name] = 0
        subjects[booking.subject_name] += 1
    
    text = [
        f"🗓 Расписание на {month_str}\n",
        "\n📊 Статистика:",
        f"- Всего занятий: {len(bookings)}",
        f"- Подтверждено: {total_confirmed}",
        f"- Ожидает подтверждения: {total_pending}",
        f"- Отменено: {total_cancelled}",
        f"- Доход за месяц: {total_income} руб.",
        "\n📈 По неделям:"
    ]
    
    for week_num in sorted(bookings_by_week.keys()):
        week_bookings = bookings_by_week[week_num]
        week_income = sum(b.price for b in week_bookings if b.status == BookingStatus.APPROVED)
        # Находим первый и последний день недели
        first_date = min(b.date for b in week_bookings)
        last_date = max(b.date for b in week_bookings)
        if first_date == last_date:
            text.append(
                f"🗓 {format_date_with_month(first_date)}: "
                f"{len(week_bookings)} занятий ({week_income} руб.)"
            )
        else:
            text.append(
                f"🗓 {format_date_with_month(first_date)}-{format_date_with_month(last_date)}: "
                f"{len(week_bookings)} занятий ({week_income} руб.)"
            )
    
    text.extend([
        "\n📚 По предметам:"
    ])
    
    for subject, count in sorted(subjects.items(), key=lambda x: x[1], reverse=True):
        text.append(f"- {subject}: {count} занятий")
    
    return "\n".join(text) 