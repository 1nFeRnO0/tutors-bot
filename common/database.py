from sqlalchemy import create_engine, Column, Integer, String, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import enum
from typing import AsyncGenerator

Base = declarative_base()

class Gender(enum.Enum):
    MALE = 'M'
    FEMALE = 'F'

class Tutor(Base):
    __tablename__ = 'tutors'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    name = Column(String)
    surname = Column(String)
    patronymic = Column(String, nullable=True)  # Отчество, опциональное
    subjects = Column(JSON)  # Список предметов
    schedule = Column(JSON)  # Расписание в формате {день: [время]}
    description = Column(String)  # Описание репетитора

class Parent(Base):
    __tablename__ = 'parents'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    name = Column(String)
    surname = Column(String)
    patronymic = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    children = relationship("Child", back_populates="parent", cascade="all, delete-orphan")

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