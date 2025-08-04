from sqlalchemy import (
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Table,
    func,
    Column,
    Integer,
    Enum,
    BigInteger,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship
from typing import List, Optional
import enum
from datetime import datetime


# Базовый класс для моделей
class Base(DeclarativeBase):
    pass


# Миксин для времени создания и обновления
class TimestampMixin:
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


# Таблица связи многие-ко-многим: пользователи и категории
user_categories = Table(
    "user_categories",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("category_id", ForeignKey("categories.id"), primary_key=True),
)

# Таблица связи многие-ко-многим: посты и категории
post_categories = Table(
    "post_categories",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id"), primary_key=True),
    Column("category_id", ForeignKey("categories.id"), primary_key=True),
)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_moderator = Column(Boolean, default=False)

    # Связи
    categories = relationship("Category", secondary=user_categories, back_populates="users")
    posts = relationship("Post", back_populates="author")
    likes = relationship("Like", back_populates="user")


class Category(Base, TimestampMixin):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Связи
    users = relationship("User", secondary=user_categories, back_populates="categories")
    posts = relationship("Post", secondary=post_categories, back_populates="categories")


class ModerationAction(enum.Enum):
    APPROVE = 1
    REJECT = 2
    REQUEST_CHANGES = 3


class Post(Base, TimestampMixin):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    city = Column(String(100), nullable=True)
    image_id = Column(String(255), nullable=True)
    is_approved = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime, nullable=True)
    
    # Новое поле: дата и время события
    event_datetime = Column(DateTime(timezone=True), nullable=True)

    # Связи
    author = relationship("User", back_populates="posts")
    categories = relationship("Category", secondary=post_categories, back_populates="posts")
    moderation_records = relationship("ModerationRecord", back_populates="post")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")


class ModerationRecord(Base, TimestampMixin):
    __tablename__ = "moderation_records"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    moderator_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    action = Column(Enum(ModerationAction), nullable=False)
    comment = Column(Text, nullable=True)

    # Связи
    post = relationship("Post", back_populates="moderation_records")
    moderator = relationship("User")


class Like(Base, TimestampMixin):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)

    # Связи
    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")

    __table_args__ = (
        # Уникальный индекс: один пользователь — один лайк на пост
        # (не реализован в коде, но нужен в БД)
    )
