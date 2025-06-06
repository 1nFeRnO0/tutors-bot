from sqlalchemy import create_engine, Column, Integer, String, JSON, ForeignKey, Enum, BigInteger, Date, Time, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import enum
from typing import AsyncGenerator
from datetime import datetime, date, time

Base = declarative_base()

class Gender(enum.Enum):
    MALE = 'M'
    FEMALE = 'F'

class BookingStatus(enum.Enum):
    """Статусы записи на занятие"""
    PENDING = 'pending'     # Ожидает подтверждения репетитора
    APPROVED = 'approved'   # Подтверждена репетитором
    REJECTED = 'rejected'   # Отклонена репетитором
    CANCELLED = 'cancelled' # Отменена родителем

class Tutor(Base):
    __tablename__ = 'tutors'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    name = Column(String)
    surname = Column(String)
    patronymic = Column(String, nullable=True)  # Отчество, опциональное
    subjects = Column(JSON)  # Список предметов
    schedule = Column(JSON)  # Расписание в формате {день: [время]}
    description = Column(String)  # Описание репетитора
    favorited_by = relationship("FavoriteTutor", back_populates="tutor", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="tutor", cascade="all, delete-orphan")

class Parent(Base):
    __tablename__ = 'parents'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True)
    name = Column(String)
    surname = Column(String)
    patronymic = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    children = relationship("Child", back_populates="parent", cascade="all, delete-orphan")
    favorite_tutors = relationship("FavoriteTutor", back_populates="parent", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="parent", cascade="all, delete-orphan")

class Child(Base):
    __tablename__ = 'children'

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('parents.id', ondelete='CASCADE'))
    name = Column(String)
    surname = Column(String)
    patronymic = Column(String, nullable=True)
    gender = Column(Enum(Gender))
    grade = Column(Integer)  # Класс обучения (1-11)
    textbook_info = Column(String)  # Информация об учебнике
    
    parent = relationship("Parent", back_populates="children")
    bookings = relationship("Booking", back_populates="child", cascade="all, delete-orphan")

class FavoriteTutor(Base):
    __tablename__ = "favorite_tutors"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("parents.id"))
    tutor_id = Column(Integer, ForeignKey("tutors.id"))
    parent = relationship("Parent", back_populates="favorite_tutors")
    tutor = relationship("Tutor", back_populates="favorited_by")

class Booking(Base):
    __tablename__ = 'bookings'
    
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('parents.id'))
    child_id = Column(Integer, ForeignKey('children.id'))
    tutor_id = Column(Integer, ForeignKey('tutors.id'))
    subject_name = Column(String)
    lesson_type = Column(String)  # 'standard' или 'exam'
    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    price = Column(Integer)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    notification_24h_sent = Column(Boolean, default=False)  # Флаг отправки уведомления за 24 часа
    notification_1h_sent = Column(Boolean, default=False)   # Флаг отправки уведомления за 1 час

    parent = relationship("Parent", back_populates="bookings")
    child = relationship("Child", back_populates="bookings")
    tutor = relationship("Tutor", back_populates="bookings")

# Создаем асинхронный движок для работы с базой данных
engine = create_async_engine(
    'sqlite+aiosqlite:///tutors.db',
    echo=True,
)

# Создаем фабрику сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session = async_session_maker()
    try:
        yield session
    finally:
        await session.close() 