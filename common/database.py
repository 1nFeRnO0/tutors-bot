from sqlalchemy import create_engine, Column, Integer, String, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base

Base = declarative_base()

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
    phone = Column(String, nullable=True)  # Телефон будем запрашивать позже

# Создаем асинхронный движок для работы с базой данных
engine = create_async_engine('sqlite+aiosqlite:///tutors.db', echo=True)

# Создаем фабрику сессий
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session 