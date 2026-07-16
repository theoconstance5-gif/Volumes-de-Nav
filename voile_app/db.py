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

# pool_pre_ping : teste chaque connexion avant de l'utiliser et la remplace
# silencieusement si elle est morte (cas fréquent avec les bases Postgres
# "serverless" comme Neon, qui peuvent fermer les connexions inactives).
# pool_recycle : force le renouvellement des connexions au bout de 5 min,
# avant qu'elles ne soient coupées côté serveur.
engine_kwargs = {"connect_args": connect_args, "pool_pre_ping": True}
if not DATABASE_URL.startswith("sqlite"):
    engine_kwargs["pool_recycle"] = 280

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False))

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
# Debrief post-régate (répond à un questionnaire d'auto-évaluation après
# chaque journée de compétition) — remplace le Google Form + VBA d'origine.
# ---------------------------------------------------------------------------

response_athlete = Table(
    "response_athlete",
    Base.metadata,
    Column("response_id", Integer, ForeignKey("debrief_responses.id", ondelete="CASCADE"), primary_key=True),
    Column("athlete_id", Integer, ForeignKey("athletes.id", ondelete="CASCADE"), primary_key=True),
)


class DebriefEpreuve(Base):
    """Épreuve / lieu de compétition (ex : Palamos, Challenge du Centre 3)."""
    __tablename__ = "debrief_epreuves"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False, unique=True)
    active = Column(Boolean, default=True, nullable=False)

    def __str__(self):
        return self.name


class DebriefCriterion(Base):
    """Critère noté de 1 à 5 dans le questionnaire (ex : « J'ai fait un bon départ »)."""
    __tablename__ = "debrief_criteria"
    id = Column(Integer, primary_key=True)
    label = Column(String(255), nullable=False, unique=True)
    position = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, default=True, nullable=False)

    def __str__(self):
        return self.label


class DebriefPoint(Base):
    """
    Point technique pouvant être choisi comme « point noir » ou « point
    positif » de la journée (ex : « Le placement au départ »).
    """
    __tablename__ = "debrief_points"
    id = Column(Integer, primary_key=True)
    label = Column(String(255), nullable=False, unique=True)
    active = Column(Boolean, default=True, nullable=False)

    def __str__(self):
        return self.label


class DebriefResponse(Base):
    """Une réponse au questionnaire = un équipage, un jour, une épreuve."""
    __tablename__ = "debrief_responses"
    id = Column(Integer, primary_key=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    epreuve_id = Column(Integer, ForeignKey("debrief_epreuves.id"), nullable=False)
    jour = Column(Integer, nullable=False)
    point_noir_id = Column(Integer, ForeignKey("debrief_points.id"), nullable=True)
    point_positif_id = Column(Integer, ForeignKey("debrief_points.id"), nullable=True)
    commentaire = Column(Text, nullable=True)

    epreuve = relationship("DebriefEpreuve")
    point_noir = relationship("DebriefPoint", foreign_keys=[point_noir_id])
    point_positif = relationship("DebriefPoint", foreign_keys=[point_positif_id])
    athletes = relationship("Athlete", secondary=response_athlete)
    ratings = relationship("DebriefRating", back_populates="response", cascade="all, delete-orphan")

    @property
    def athletes_label(self):
        return " / ".join(a.full_name for a in self.athletes) or "—"


class DebriefRating(Base):
    """Note de 1 à 5 donnée à un critère, pour une réponse donnée."""
    __tablename__ = "debrief_ratings"
    id = Column(Integer, primary_key=True)
    response_id = Column(Integer, ForeignKey("debrief_responses.id", ondelete="CASCADE"), nullable=False)
    criterion_id = Column(Integer, ForeignKey("debrief_criteria.id"), nullable=False)
    value = Column(Integer, nullable=False)  # 1 à 5

    response = relationship("DebriefResponse", back_populates="ratings")
    criterion = relationship("DebriefCriterion")


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
            # Ne seed les athlètes de démo que si les groupes de démo existent
            # encore (premier lancement). Si l'utilisateur a déjà renommé ou
            # supprimé ces groupes, on ne force rien : il gérera ses propres
            # athlètes depuis Configuration.
            if elite and espoirs:
                demo = [
                    Athlete(first_name="Léa", last_name="Martin", group_id=elite.id),
                    Athlete(first_name="Hugo", last_name="Bernard", group_id=elite.id),
                    Athlete(first_name="Chloé", last_name="Petit", group_id=espoirs.id),
                    Athlete(first_name="Nolan", last_name="Robert", group_id=espoirs.id),
                ]
                db.add_all(demo)
                db.commit()

        if db.query(DebriefCriterion).count() == 0:
            criteria = [
                "J'ai fait un bon départ",
                "J'avais une bonne vitesse au près",
                "J'avais une bonne vitesse au largue",
                "J'ai fait de belles enroulées de marque",
                "J'ai suivi mon plan stratégique",
                "Physiquement à la fin de la journée j'étais plutôt",
                "Mentalement j'ai réussi à rester solide tout au long de la journée",
                "La communication à bord était",
                "J'avais une bonne vitesse sous spi",
            ]
            db.add_all([DebriefCriterion(label=c, position=i) for i, c in enumerate(criteria)])
            db.commit()

        if db.query(DebriefPoint).count() == 0:
            points = [
                "Le placement au départ", "Le timing de lancement au départ",
                "La tenue de ma place en post départ", "La conduite du bateau au près",
                "Les réglages des voiles au près", "La conduite du bateau au largue",
                "Les réglages des voiles au largue", "La conduite du bateau au vent arrière",
                "Les réglages des voiles au vent arrière", "Les réglages statiques du bateau",
                "Les envois de spi", "Les passages de marque sous le vent",
                "La gestion de la flotte", "Le suivi du vent",
                "La fatigue mentale", "La fatigue musculaire",
                "La communication à bord",
            ]
            db.add_all([DebriefPoint(label=p) for p in points])
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
