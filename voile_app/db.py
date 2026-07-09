"""
Module de base de données pour l'application de suivi d'entraînement voile.

Utilise SQLAlchemy afin de pouvoir basculer facilement entre SQLite (usage
local / test) et une base PostgreSQL hébergée (usage en production, accès
partagé multi-entraîneurs).

La connexion est définie par la variable d'environnement DATABASE_URL,
ou via st.secrets["DATABASE_URL"] quand l'app tourne sur Streamlit Cloud.
Par défaut, on utilise un fichier SQLite local (voile.db).
"""

import os
from datetime import date, datetime, time

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime, Time,
    ForeignKey, Boolean, Table, Text, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session


def _get_database_url() -> str:
    # 1) variable d'environnement
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    # 2) secrets Streamlit (si dispo, sans planter en dehors de Streamlit)
    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    # 3) valeur par défaut : SQLite local
    return "sqlite:///voile.db"


DATABASE_URL = _get_database_url()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))

Base = declarative_base()


# ---------------------------------------------------------------------------
# Tables d'association
# ---------------------------------------------------------------------------

session_athlete = Table(
    "session_athlete",
    Base.metadata,
    Column("session_id", Integer, ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True),
    Column("athlete_id", Integer, ForeignKey("athletes.id", ondelete="CASCADE"), primary_key=True),
)


# ---------------------------------------------------------------------------
# Listes de référence (configurables)
# ---------------------------------------------------------------------------

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    active = Column(Boolean, default=True, nullable=False)

    athletes = relationship("Athlete", back_populates="group")

    def __str__(self):
        return self.name


class Athlete(Base):
    __tablename__ = "athletes"
    id = Column(Integer, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"))
    active = Column(Boolean, default=True, nullable=False)

    group = relationship("Group", back_populates="athletes")
    sessions = relationship("TrainingSession", secondary=session_athlete, back_populates="athletes")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name


class Spot(Base):
    __tablename__ = "spots"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, unique=True)
    active = Column(Boolean, default=True, nullable=False)

    def __str__(self):
        return self.name


class Theme(Base):
    __tablename__ = "themes"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, unique=True)
    active = Column(Boolean, default=True, nullable=False)

    def __str__(self):
        return self.name


class WindTranche(Base):
    """
    Tranches de vent configurables utilisées pour répartir le temps de
    navigation de chaque séance (ex: 0-10 nds / 10-17 nds / +17 nds).
    """
    __tablename__ = "wind_tranches"
    id = Column(Integer, primary_key=True)
    label = Column(String(100), nullable=False, unique=True)
    min_knots = Column(Float, nullable=False)
    max_knots = Column(Float, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    def __str__(self):
        return self.label

    def contains(self, speed: float) -> bool:
        return self.min_knots <= speed <= self.max_knots


# ---------------------------------------------------------------------------
# Séances d'entraînement
# ---------------------------------------------------------------------------

class TrainingSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    session_date = Column(Date, nullable=False, default=date.today)

    spot_id = Column(Integer, ForeignKey("spots.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)

    # Horaires de la séance : le volume (duration_hours) est calculé à la
    # saisie à partir de ces deux heures.
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_hours = Column(Float, nullable=False)

    comments = Column(Text, nullable=True)
    coach_name = Column(String(120), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    spot = relationship("Spot")
    group = relationship("Group")
    athletes = relationship("Athlete", secondary=session_athlete, back_populates="sessions")
    wind_splits = relationship(
        "SessionWindSplit", back_populates="session", cascade="all, delete-orphan"
    )
    theme_splits = relationship(
        "SessionThemeSplit", back_populates="session", cascade="all, delete-orphan"
    )


class SessionWindSplit(Base):
    """
    Répartition du temps de navigation d'une séance entre plusieurs tranches
    de vent (ex : 1h en 0-10 nds, 0h30 en 10-17 nds). La somme des heures
    des splits d'une séance doit égaler sa duration_hours.
    """
    __tablename__ = "session_wind_splits"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    wind_tranche_id = Column(Integer, ForeignKey("wind_tranches.id"), nullable=False)
    hours = Column(Float, nullable=False)

    session = relationship("TrainingSession", back_populates="wind_splits")
    wind_tranche = relationship("WindTranche")


class SessionThemeSplit(Base):
    """
    Répartition du temps de navigation d'une séance entre 1 ou 2 thématiques
    de travail (ex : 1h30 Portant, 1h Spi). La somme des heures des splits
    d'une séance doit égaler sa duration_hours.
    """
    __tablename__ = "session_theme_splits"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    theme_id = Column(Integer, ForeignKey("themes.id"), nullable=False)
    hours = Column(Float, nullable=False)

    session = relationship("TrainingSession", back_populates="theme_splits")
    theme = relationship("Theme")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def init_db(seed_if_empty: bool = True):
    """Crée les tables si nécessaire et insère des données d'exemple."""
    Base.metadata.create_all(engine)
    if seed_if_empty:
        _seed_defaults()


def _seed_defaults():
    db = SessionLocal()
    try:
        if db.query(Group).count() == 0:
            groups = [Group(name=n) for n in ["Elite", "Espoirs", "Perfectionnement", "Découverte"]]
            db.add_all(groups)
            db.commit()

        if db.query(WindTranche).count() == 0:
            tranches = [
                WindTranche(label="0-10 nds", min_knots=0, max_knots=10),
                WindTranche(label="10-17 nds", min_knots=10, max_knots=17),
                WindTranche(label="+17 nds", min_knots=17, max_knots=50),
            ]
            db.add_all(tranches)
            db.commit()

        if db.query(Theme).count() == 0:
            themes = [Theme(name=n) for n in [
                "Départs / arrivées", "Portant", "Près", "Spi", "Régates / parcours",
                "Physique", "Réglages", "Tactique"
            ]]
            db.add_all(themes)
            db.commit()

        if db.query(Spot).count() == 0:
            spots = [Spot(name=n) for n in ["Plan d'eau principal", "Baie extérieure", "Bassin abrité"]]
            db.add_all(spots)
            db.commit()

        if db.query(Athlete).count() == 0:
            elite = db.query(Group).filter_by(name="Elite").first()
            espoirs = db.query(Group).filter_by(name="Espoirs").first()
            demo = [
                Athlete(first_name="Léa", last_name="Martin", group_id=elite.id),
                Athlete(first_name="Hugo", last_name="Bernard", group_id=elite.id),
                Athlete(first_name="Chloé", last_name="Petit", group_id=espoirs.id),
                Athlete(first_name="Nolan", last_name="Robert", group_id=espoirs.id),
            ]
            db.add_all(demo)
            db.commit()
    finally:
        db.close()


def get_db():
    """Retourne une session SQLAlchemy (à fermer par l'appelant)."""
    return SessionLocal()


def compute_duration_hours(start: time, end: time) -> float:
    """Calcule la durée en heures (décimales) entre deux heures de la journée."""
    delta = datetime.combine(date.min, end) - datetime.combine(date.min, start)
    return round(delta.total_seconds() / 3600, 4)
