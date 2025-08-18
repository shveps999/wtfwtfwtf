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
    BigInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship
from sqlalchemy.orm import Mapped
from typing import List, Optional
from enum import Enum


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


user_categories = Table(
    "user_categories",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("category_id", ForeignKey("categories.id"), primary_key=True),
)

post_categories = Table(
    "post_categories",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id"), primary_key=True),
    Column("category_id", ForeignKey("categories.id"), primary_key=True),
)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    categories: Mapped[List["Category"]] = relationship(
        secondary=user_categories, back_populates="users"
    )
    posts: Mapped[List["Post"]] = relationship(back_populates="author")


class Category(Base, TimestampMixin):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[List[User]] = relationship(
        secondary=user_categories, back_populates="categories"
    )
    posts: Mapped[List["Post"]] = relationship(
        secondary=post_categories, back_populates="categories"
    )


class Post(Base, TimestampMixin):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    image_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    event_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # ← Новое поле

    author: Mapped[User] = relationship(back_populates="posts")
    categories: Mapped[List[Category]] = relationship(
        secondary=post_categories, back_populates="posts"
    )
    moderation_records: Mapped[List["ModerationRecord"]] = relationship(
        back_populates="post"
    )


class ModerationRecord(Base, TimestampMixin):
    __tablename__ = "moderation_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    moderator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    post: Mapped[Post] = relationship(back_populates="moderation_records")
    moderator: Mapped[User] = relationship()


class Like(Base, TimestampMixin):
    __tablename__ = "likes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)

    user: Mapped[User] = relationship()
    post: Mapped[Post] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_like_user_post"),
    )


class ModerationAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"
