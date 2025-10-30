"""Databázové modely pro KvízArénu.

Tento modul definuje instanci SQLAlchemy a všechny databázové modely
(tabulky) pro aplikaci."""

from __future__ import annotations

import time
import uuid

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Boolean,
    Engine,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


db = SQLAlchemy()


DEFAULT_QUESTION_TIME_LIMIT = 15


class Otazka(db.Model):
    """Model pro jednotlivou kvízovou otázku."""

    __tablename__ = "otazky"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    otazka: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    spravna_odpoved: Mapped[str] = mapped_column(Text, nullable=False)
    spatna_odpoved1: Mapped[str] = mapped_column(Text, nullable=False)
    spatna_odpoved2: Mapped[str] = mapped_column(Text, nullable=False)
    spatna_odpoved3: Mapped[str] = mapped_column(Text, nullable=False)
    tema: Mapped[str | None] = mapped_column(String(255), nullable=True)
    obtiznost: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    zdroj_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    kvizy_v_kterych_je: Mapped[list["KvizOtazky"]] = relationship(
        "KvizOtazky", back_populates="otazka", cascade="all, delete-orphan"
    )


class Kviz(db.Model):
    """Model pro jeden kvíz (sada otázek)."""

    __tablename__ = "kvizy"

    kviz_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nazev: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    popis: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_limit_per_question: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_QUESTION_TIME_LIMIT
    )

    otazky_v_kvizu: Mapped[list["KvizOtazky"]] = relationship(
        "KvizOtazky",
        back_populates="kviz",
        cascade="all, delete-orphan",
        order_by="KvizOtazky.poradi",
    )


class KvizOtazky(db.Model):
    """Spojovací tabulka mezi kvízy a otázkami."""

    __tablename__ = "kviz_otazky"
    __table_args__ = (
        UniqueConstraint("kviz_id_fk", "otazka_id_fk", name="uq_kviz_otazka"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kviz_id_fk: Mapped[int] = mapped_column(
        ForeignKey("kvizy.kviz_id", ondelete="CASCADE"), nullable=False
    )
    otazka_id_fk: Mapped[int] = mapped_column(
        ForeignKey("otazky.id", ondelete="CASCADE"), nullable=False
    )
    poradi: Mapped[int] = mapped_column(Integer, nullable=False)

    kviz: Mapped["Kviz"] = relationship("Kviz", back_populates="otazky_v_kvizu")
    otazka: Mapped["Otazka"] = relationship(
        "Otazka", back_populates="kvizy_v_kterych_je"
    )


class GameSession(db.Model):
    """Model pro jedno herní sezení."""

    __tablename__ = "game_sessions"

    session_id: Mapped[str] = mapped_column(
        String(255), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    kviz_id_fk: Mapped[int] = mapped_column(
        ForeignKey("kvizy.kviz_id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_question_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_question_timestamp: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(time.time())
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    kviz: Mapped["Kviz"] = relationship("Kviz")


def init_app(app: Flask) -> None:
    """Inicializuje SQLAlchemy a CLI příkazy pro zadanou Flask aplikaci."""

    db.init_app(app)

    if "init-db" not in app.cli.commands:
        @app.cli.command("init-db")
        def init_db_command() -> None:
            """Vytvoří databázové tabulky."""

            db.create_all()
            click.echo("Databáze úspěšně inicializována.")


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """Zajistí zapnutí podpory cizích klíčů ve SQLite."""

    if dbapi_connection.__class__.__module__ == "sqlite3":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
