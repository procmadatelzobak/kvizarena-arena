"""
Databázové modely pro KvízArénu (s použitím Flask-SQLAlchemy).

Tento soubor definuje `db` instanci a všechny databázové modely
(tabulky) pro aplikaci.
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

# Instance SQLAlchemy, inicializovaná v app.py
db = SQLAlchemy()

DEFAULT_QUESTION_TIME_LIMIT = 15  # Výchozí čas na otázku v sekundách

# --- Modely pro Správu Kvízů (Import z Vševěda) ---

class Otazka(db.Model):
    """
    Model pro jednotlivou kvízovou otázku.
    Text otázky musí být unikátní.
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

    # Vztah pro spojovací tabulku (aby se dalo snadno smazat)
    kvizy_v_kterych_je = relationship("KvizOtazky", back_populates="otazka", cascade="all, delete-orphan")

class Kviz(db.Model):
    """
    Model pro jeden kvíz (sada otázek).
    Název kvízu musí být unikátní.
    """
    __tablename__ = "kvizy"

    kviz_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nazev: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    popis: Mapped[str] = mapped_column(Text, nullable=True)
    time_limit_per_question: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_QUESTION_TIME_LIMIT
    )

    # Vztah (relationship) pro přístup k otázkám přes spojovací tabulku
    otazky_v_kvizu = relationship(
        "KvizOtazky",
        back_populates="kviz",
        cascade="all, delete-orphan",
        order_by="KvizOtazky.poradi"  # Klíčové: zajistí správné pořadí
    )

class KvizOtazky(db.Model):
    """
    Spojovací tabulka (Association Table) mezi Kvízy a Otázkami.
    Udržuje pořadí otázek v daném kvízu.
    """
    __tablename__ = "kviz_otazky"
    __table_args__ = (
        UniqueConstraint('kviz_id_fk', 'otazka_id_fk', name='uq_kviz_otazka'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kviz_id_fk: Mapped[int] = mapped_column(ForeignKey("kvizy.kviz_id"))
    otazka_id_fk: Mapped[int] = mapped_column(ForeignKey("otazky.id"))
    poradi: Mapped[int] = mapped_column(Integer, nullable=False)

    # Vztahy (relationships) pro snadný přístup k objektům
    kviz: Mapped["Kviz"] = relationship("Kviz", back_populates="otazky_v_kvizu")
    otazka: Mapped["Otazka"] = relationship("Otazka", back_populates="kvizy_v_kterych_je")

# --- Modely pro Herní Logiku (MVP) ---

class GameSession(db.Model):
    """
    Model pro jednu rozehranou hru (herní sezení).
    Pro MVP je session_id náš "anonymní uživatel".
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

    # Vztah pro snadný přístup k informacím o kvízu
    kviz: Mapped["Kviz"] = relationship("Kviz")

def init_app(app: Flask) -> None:
    """
    Inicializuje SQLAlchemy rozšíření s danou Flask aplikací
    a zaregistruje CLI příkaz 'init-db'.
    """
    db.init_app(app)

    @app.cli.command("init-db")
    def init_db_command():
        """Vytvoří databázové tabulky."""
        with app.app_context():
            db.create_all()
        print("Databáze úspěšně inicializována.")

# Zajistíme podporu pro cizí klíče (FOREIGN KEYs) ve SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__ == "sqlite3":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
