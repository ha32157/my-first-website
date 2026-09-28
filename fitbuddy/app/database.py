from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    goal: Mapped[str] = mapped_column(String(40), nullable=False)
    intensity: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    plans: Mapped[list["WorkoutPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_plan: Mapped[str] = mapped_column(Text, nullable=False)
    updated_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    nutrition_tip: Mapped[str] = mapped_column(Text, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user: Mapped[User] = relationship(back_populates="plans")


settings = get_settings()
if settings.database_url.startswith("sqlite"):
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
else:
    engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_user(db: Session, *, user_id: str, name: str, age: int, weight_kg: float, goal: str, intensity: str) -> User:
    user = db.query(User).filter(User.user_id == user_id).one_or_none()
    if user is None:
        user = User(user_id=user_id, name=name, age=age, weight_kg=weight_kg, goal=goal, intensity=intensity)
        db.add(user)
    else:
        user.name = name
        user.age = age
        user.weight_kg = weight_kg
        user.goal = goal
        user.intensity = intensity
    db.commit()
    db.refresh(user)
    return user


def save_plan(db: Session, *, user: User, original_plan: str, nutrition_tip: str) -> WorkoutPlan:
    plan = WorkoutPlan(user_id=user.id, original_plan=original_plan, nutrition_tip=nutrition_tip)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_plan(db: Session, *, plan: WorkoutPlan, updated_plan: str, feedback: str, nutrition_tip: str) -> WorkoutPlan:
    plan.updated_plan = updated_plan
    plan.feedback = feedback
    plan.nutrition_tip = nutrition_tip
    plan.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(plan)
    return plan


def get_user(db: Session, user_id: str) -> User | None:
    return db.query(User).filter(User.user_id == user_id).one_or_none()


def get_latest_plan(db: Session, user: User) -> WorkoutPlan | None:
    return db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).order_by(WorkoutPlan.id.desc()).first()


def get_all_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()
