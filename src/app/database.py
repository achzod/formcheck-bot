from __future__ import annotations

import datetime as dt
from typing import Sequence

from sqlalchemy import ForeignKey, String, Text, func, select, update
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
    morpho_profiles: Mapped[list[MorphoProfileDB]] = relationship(back_populates="user")


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


class MorphoProfileDB(Base):
    """Profil morphologique d'un client (issu de l'analyse de 3 photos statiques)."""
    __tablename__ = "morpho_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Mesures normalisees
    shoulder_width: Mapped[float] = mapped_column(default=0.0)
    hip_width: Mapped[float] = mapped_column(default=0.0)
    femur_length: Mapped[float] = mapped_column(default=0.0)
    tibia_length: Mapped[float] = mapped_column(default=0.0)
    torso_length: Mapped[float] = mapped_column(default=0.0)
    upper_arm_length: Mapped[float] = mapped_column(default=0.0)
    forearm_length: Mapped[float] = mapped_column(default=0.0)
    total_arm_length: Mapped[float] = mapped_column(default=0.0)
    # Ratios
    femur_tibia_ratio: Mapped[float] = mapped_column(default=1.0)
    torso_femur_ratio: Mapped[float] = mapped_column(default=1.0)
    arm_torso_ratio: Mapped[float] = mapped_column(default=1.0)
    shoulder_hip_ratio: Mapped[float] = mapped_column(default=1.0)
    upper_arm_forearm_ratio: Mapped[float] = mapped_column(default=1.0)
    # Classification
    morpho_type: Mapped[str] = mapped_column(String(30), default="mesomorphe")
    squat_type: Mapped[str] = mapped_column(String(30), default="balanced")
    deadlift_type: Mapped[str] = mapped_column(String(30), default="conventional")
    bench_grip: Mapped[str] = mapped_column(String(30), default="moyen")
    biceps_type: Mapped[str] = mapped_column(String(30), default="moyen")
    # Textuel
    posture_notes: Mapped[str | None] = mapped_column(Text, default=None)
    recommendations: Mapped[str | None] = mapped_column(Text, default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    # JSON complet pour les donnees detaillees
    full_json: Mapped[str | None] = mapped_column(Text, default=None)
    # Meta
    analysis_quality: Mapped[float] = mapped_column(default=0.0)
    photos_analyzed: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now())

    user: Mapped[User] = relationship(back_populates="morpho_profiles")


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


# ── Morpho Profile CRUD ───────────────────────────────────────────────────


async def save_morpho_profile(user_id: int, morpho_data: dict) -> MorphoProfileDB:
    """Sauvegarde un profil morphologique. Remplace le precedent si existant."""
    import json

    async with async_session() as session:
        # Supprimer l'ancien profil s'il existe
        existing = await session.execute(
            select(MorphoProfileDB).where(MorphoProfileDB.user_id == user_id)
        )
        old = existing.scalar_one_or_none()
        if old:
            await session.delete(old)
            await session.flush()

        profile = MorphoProfileDB(
            user_id=user_id,
            shoulder_width=morpho_data.get("shoulder_width", 0.0),
            hip_width=morpho_data.get("hip_width", 0.0),
            femur_length=morpho_data.get("femur_length", 0.0),
            tibia_length=morpho_data.get("tibia_length", 0.0),
            torso_length=morpho_data.get("torso_length", 0.0),
            upper_arm_length=morpho_data.get("upper_arm_length", 0.0),
            forearm_length=morpho_data.get("forearm_length", 0.0),
            total_arm_length=morpho_data.get("total_arm_length", 0.0),
            femur_tibia_ratio=morpho_data.get("femur_tibia_ratio", 1.0),
            torso_femur_ratio=morpho_data.get("torso_femur_ratio", 1.0),
            arm_torso_ratio=morpho_data.get("arm_torso_ratio", 1.0),
            shoulder_hip_ratio=morpho_data.get("shoulder_hip_ratio", 1.0),
            upper_arm_forearm_ratio=morpho_data.get("upper_arm_forearm_ratio", 1.0),
            morpho_type=morpho_data.get("morpho_type", "mesomorphe"),
            squat_type=morpho_data.get("squat_type", "balanced"),
            deadlift_type=morpho_data.get("deadlift_type", "conventional"),
            bench_grip=morpho_data.get("bench_grip", "moyen"),
            biceps_type=morpho_data.get("biceps_type", "moyen"),
            posture_notes=morpho_data.get("posture", {}).get("summary", ""),
            recommendations="\n".join(morpho_data.get("recommendations", [])),
            summary=morpho_data.get("summary", ""),
            full_json=json.dumps(morpho_data, ensure_ascii=False),
            analysis_quality=morpho_data.get("analysis_quality", 0.0),
            photos_analyzed=",".join(morpho_data.get("photos_analyzed", [])),
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile


async def get_morpho_profile(user_id: int) -> MorphoProfileDB | None:
    """Recupere le profil morpho d'un utilisateur."""
    async with async_session() as session:
        result = await session.execute(
            select(MorphoProfileDB).where(MorphoProfileDB.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def has_morpho_profile(user_id: int) -> bool:
    """Verifie si un utilisateur a un profil morpho."""
    profile = await get_morpho_profile(user_id)
    return profile is not None


async def get_morpho_profile_dict(user_id: int) -> dict | None:
    """Recupere le profil morpho sous forme de dict complet (depuis full_json)."""
    import json

    profile = await get_morpho_profile(user_id)
    if not profile:
        return None
    if profile.full_json:
        try:
            return json.loads(profile.full_json)
        except json.JSONDecodeError:
            pass
    # Fallback : construire le dict depuis les colonnes
    return {
        "shoulder_width": profile.shoulder_width,
        "hip_width": profile.hip_width,
        "femur_length": profile.femur_length,
        "tibia_length": profile.tibia_length,
        "torso_length": profile.torso_length,
        "upper_arm_length": profile.upper_arm_length,
        "forearm_length": profile.forearm_length,
        "total_arm_length": profile.total_arm_length,
        "femur_tibia_ratio": profile.femur_tibia_ratio,
        "torso_femur_ratio": profile.torso_femur_ratio,
        "arm_torso_ratio": profile.arm_torso_ratio,
        "shoulder_hip_ratio": profile.shoulder_hip_ratio,
        "upper_arm_forearm_ratio": profile.upper_arm_forearm_ratio,
        "morpho_type": profile.morpho_type,
        "squat_type": profile.squat_type,
        "deadlift_type": profile.deadlift_type,
        "bench_grip": profile.bench_grip,
        "biceps_type": profile.biceps_type,
        "posture_notes": profile.posture_notes,
        "recommendations": profile.recommendations.split("\n") if profile.recommendations else [],
        "summary": profile.summary,
        "analysis_quality": profile.analysis_quality,
        "photos_analyzed": profile.photos_analyzed.split(",") if profile.photos_analyzed else [],
    }
