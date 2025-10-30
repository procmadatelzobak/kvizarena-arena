"""
Database models for KvizArena (using Flask-SQLAlchemy).

This file defines the `db` instance and all database models (tables)
for the application.
"""

from __future__ import annotations
import uuid
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Integer, String, Text, ForeignKey, UniqueConstraint, event, Engine
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# SQLAlchemy instance, initialized in app.py
db = SQLAlchemy()

DEFAULT_QUESTION_TIME_LIMIT = 15  # Default time per question in seconds

# --- Models for Quiz Management (Imported from Vševěd) ---

class Otazka(db.Model):
    """
    Model for an individual quiz question.
    The question text must be unique.
    """
    __tablename__ = "otazky"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    otazka: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    spravna_odpoved: Mapped[str] = mapped_column(Text, nullable=False)
    spatna_odpoved1: Mapped[str] = mapped_column(Text, nullable=False)
    spatna_odpoved2: Mapped[str] = mapped_column(Text, nullable=False)
    spatna_odpoved3: Mapped[str] = mapped_column(Text, nullable=False)
    tema: Mapped[str] = mapped_column(String(255), nullable=True)
    obtiznost: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    zdroj_url: Mapped[str] = mapped_column(Text, nullable=True)

    # Relationship for the association table (for easy deletion)
    kvizy_v_kterych_je = relationship("KvizOtazky", back_populates="otazka", cascade="all, delete-orphan")

class Kviz(db.Model):
    """
    Model for a single quiz (a set of questions).
    The quiz name must be unique.
    """
    __tablename__ = "kvizy"

    kviz_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nazev: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    popis: Mapped[str] = mapped_column(Text, nullable=True)
    time_limit_per_question: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_QUESTION_TIME_LIMIT
    )

    # Relationship to access questions via the association table
    otazky_v_kvizu = relationship(
        "KvizOtazky",
        back_populates="kviz",
        cascade="all, delete-orphan",
        order_by="KvizOtazky.poradi"  # Crucial: ensures correct question order
    )

class KvizOtazky(db.Model):
    """
    Association Table between Kvizy and Otazky.
    Maintains the order of questions in a quiz.
    """
    __tablename__ = "kviz_otazky"
    __table_args__ = (
        UniqueConstraint('kviz_id_fk', 'otazka_id_fk', name='uq_kviz_otazka'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kviz_id_fk: Mapped[int] = mapped_column(ForeignKey("kvizy.kviz_id"))
    otazka_id_fk: Mapped[int] = mapped_column(ForeignKey("otazky.id"))
    poradi: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships for easy access to objects
    kviz: Mapped["Kviz"] = relationship("Kviz", back_populates="otazky_v_kvizu")
    otazka: Mapped["Otazka"] = relationship("Otazka", back_populates="kvizy_v_kterych_je")

# --- Models for Game Logic (MVP) ---

class GameSession(db.Model):
    """
    Model for a single active game (a game session).
    For MVP, session_id is our "anonymous user".
    """
    __tablename__ = "game_sessions"

    session_id: Mapped[str] = mapped_column(
        String(255), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    kviz_id_fk: Mapped[int] = mapped_column(ForeignKey("kvizy.kviz_id"))
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_question_timestamp: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(time.time())
    )
    is_active: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=True)

    # Relationship for easy access to quiz info
    kviz: Mapped["Kviz"] = relationship("Kviz")

def init_app(app: Flask) -> None:
    """
    Initializes the SQLAlchemy extension with the given Flask app
    and registers the 'init-db' CLI command.
    """
    db.init_app(app)

    @app.cli.command("init-db")
    def init_db_command():
        """Creates the database tables."""
        with app.app_context():
            db.create_all()
        print("Database initialized successfully.")

# Ensure SQLite enforces FOREIGN KEY constraints
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__ == "sqlite3":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
