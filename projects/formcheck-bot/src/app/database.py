from __future__ import annotations

import datetime as dt
from typing import Sequence

from sqlalchemy import ForeignKey, String, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ── Models ──────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(100), default=None)
    credits: Mapped[int] = mapped_column(default=0)
    is_unlimited: Mapped[bool] = mapped_column(default=False)
    unlimited_expires_at: Mapped[dt.datetime | None] = mapped_column(default=None)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    analyses: Mapped[list[Analysis]] = relationship(back_populates="user")
    payments: Mapped[list[Payment]] = relationship(back_populates="user")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    video_path: Mapped[str | None] = mapped_column(default=None)
    exercise: Mapped[str | None] = mapped_column(default=None)
    score: Mapped[int | None] = mapped_column(default=None)
    report: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    user: Mapped[User] = relationship(back_populates="analyses")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    stripe_session_id: Mapped[str] = mapped_column(String(255), unique=True)
    amount: Mapped[int] = mapped_column()  # cents
    plan: Mapped[str] = mapped_column(String(50))
    credits_added: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    user: Mapped[User] = relationship(back_populates="payments")


# ── Init ────────────────────────────────────────────────────────────────


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── CRUD ────────────────────────────────────────────────────────────────


async def get_or_create_user(phone: str, name: str | None = None) -> tuple[User, bool]:
    """Return (user, created). *created* is True when the user is new."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()
        if user:
            return user, False

        user = User(phone=phone, name=name, credits=1)  # 1 free analysis
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user, True


async def get_user_by_phone(phone: str) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()


async def has_credits(user: User) -> bool:
    """Check if user can perform an analysis (credits > 0 or active unlimited)."""
    if user.is_unlimited and user.unlimited_expires_at:
        if user.unlimited_expires_at > dt.datetime.utcnow():
            return True
        # Expired — disable unlimited
        async with async_session() as session:
            await session.execute(
                update(User)
                .where(User.id == user.id)
                .values(is_unlimited=False, unlimited_expires_at=None)
            )
            await session.commit()
        return user.credits > 0
    return user.credits > 0


async def decrement_credit(user_id: int) -> None:
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user and not user.is_unlimited and user.credits > 0:
            user.credits -= 1
            await session.commit()


async def add_credits(user_id: int, credits: int) -> User | None:
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.credits += credits
            await session.commit()
            await session.refresh(user)
        return user


async def set_unlimited(user_id: int) -> User | None:
    async with async_session() as session:
        user = await session.get(User, user_id)
        if user:
            user.is_unlimited = True
            user.unlimited_expires_at = dt.datetime.utcnow() + dt.timedelta(days=365)
            await session.commit()
            await session.refresh(user)
        return user


async def create_analysis(
    user_id: int,
    video_path: str | None = None,
    exercise: str | None = None,
    score: int | None = None,
    report: str | None = None,
) -> Analysis:
    async with async_session() as session:
        analysis = Analysis(
            user_id=user_id,
            video_path=video_path,
            exercise=exercise,
            score=score,
            report=report,
        )
        session.add(analysis)
        await session.commit()
        await session.refresh(analysis)
        return analysis


async def update_analysis(
    analysis_id: int,
    exercise: str | None = None,
    score: int | None = None,
    report: str | None = None,
) -> Analysis | None:
    async with async_session() as session:
        analysis = await session.get(Analysis, analysis_id)
        if analysis:
            if exercise is not None:
                analysis.exercise = exercise
            if score is not None:
                analysis.score = score
            if report is not None:
                analysis.report = report
            await session.commit()
            await session.refresh(analysis)
        return analysis


async def create_payment(
    user_id: int,
    stripe_session_id: str,
    amount: int,
    plan: str,
    credits_added: int,
) -> Payment:
    async with async_session() as session:
        payment = Payment(
            user_id=user_id,
            stripe_session_id=stripe_session_id,
            amount=amount,
            plan=plan,
            credits_added=credits_added,
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment


async def get_payment_by_session_id(session_id: str) -> Payment | None:
    """Check if a Stripe session was already processed (idempotency)."""
    async with async_session() as session:
        result = await session.execute(
            select(Payment).where(Payment.stripe_session_id == session_id)
        )
        return result.scalar_one_or_none()


async def get_user_analyses(user_id: int) -> Sequence[Analysis]:
    async with async_session() as session:
        result = await session.execute(
            select(Analysis).where(Analysis.user_id == user_id).order_by(Analysis.created_at.desc())
        )
        return result.scalars().all()
