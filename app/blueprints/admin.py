"""Flask blueprint for administrating quizzes in KvízAréna."""

from __future__ import annotations

import csv
import io
import logging
from typing import Iterable

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from app.database import (
    DEFAULT_QUESTION_TIME_LIMIT,
    Kviz,
    KvizOtazky,
    Otazka,
    db,
)

LOGGER = logging.getLogger(__name__)


def _safe_int(value: str | None, default: int) -> int:
    """Convert ``value`` to ``int`` or return ``default`` if conversion fails."""

    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _count_questions(quizzes: Iterable[Kviz]) -> list[dict[str, object]]:
    """Return metadata with question counts for provided quizzes."""

    results: list[dict[str, object]] = []
    for quiz in quizzes:
        question_count = (
            db.session.query(KvizOtazky)
            .filter_by(kviz_id_fk=quiz.kviz_id)
            .count()
        )
        results.append({"kviz": quiz, "pocet_otazek": question_count})

    return results


def create_admin_blueprint() -> Blueprint:
    """Create blueprint with administrative endpoints."""

    blueprint = Blueprint(
        "admin",
        __name__,
        url_prefix="/admin",
        template_folder="../templates/admin",
    )

    @blueprint.route("/kvizy", methods=["GET", "POST"])
    def kvizy_route():
        """Display quizzes and handle creation of new ones."""

        if request.method == "POST":
            name = request.form.get("quiz_name", "").strip()
            description = request.form.get("quiz_description", "").strip()
            time_limit = _safe_int(
                request.form.get("time_limit"), DEFAULT_QUESTION_TIME_LIMIT
            )

            if not name:
                flash("Název kvízu nesmí být prázdný.", "warning")
            elif Kviz.query.filter_by(nazev=name).first():
                flash(f"Kvíz s názvem '{name}' již existuje.", "error")
            else:
                try:
                    new_quiz = Kviz(
                        nazev=name,
                        popis=description,
                        time_limit_per_question=time_limit,
                    )
                    db.session.add(new_quiz)
                    db.session.commit()
                    flash(f"Kvíz '{name}' byl úspěšně vytvořen.", "success")
                    return redirect(url_for("admin.kvizy_route"))
                except SQLAlchemyError as exc:
                    db.session.rollback()
                    LOGGER.exception("Failed to create quiz '%s'", name)
                    flash(
                        f"Došlo k chybě při vytváření kvízu: {exc}",
                        "error",
                    )

        quizzes = Kviz.query.order_by(Kviz.nazev).all()
        quizzes_with_counts = _count_questions(quizzes)
        return render_template(
            "kvizy.html",
            quizzes_with_counts=quizzes_with_counts,
        )

    @blueprint.post("/kviz/delete/<int:kviz_id>")
    def delete_quiz_route(kviz_id: int):
        """Delete quiz and its relations via cascading."""

        quiz = Kviz.query.get_or_404(kviz_id)
        try:
            db.session.delete(quiz)
            db.session.commit()
            flash(f"Kvíz '{quiz.nazev}' byl úspěšně smazán.", "success")
        except SQLAlchemyError as exc:
            db.session.rollback()
            LOGGER.exception("Failed to delete quiz %s", kviz_id)
            flash(f"Chyba při mazání kvízu: {exc}", "error")

        return redirect(url_for("admin.kvizy_route"))

    @blueprint.post("/kviz/import")
    def import_quiz_csv():
        """Import quiz and questions from uploaded CSV file."""

        quiz_name = request.form.get("quiz_name", "").strip()
        quiz_description = request.form.get("quiz_description", "").strip()
        time_limit = _safe_int(
            request.form.get("time_limit"), DEFAULT_QUESTION_TIME_LIMIT
        )
        file = request.files.get("csv_file")

        if not quiz_name or file is None or file.filename == "":
            flash("Název kvízu a CSV soubor jsou povinné.", "error")
            return redirect(url_for("admin.kvizy_route"))

        if Kviz.query.filter_by(nazev=quiz_name).first():
            flash(
                f"Kvíz s názvem '{quiz_name}' již existuje. Zvolte jiný název.",
                "error",
            )
            return redirect(url_for("admin.kvizy_route"))

        if not file.filename.lower().endswith(".csv"):
            flash("Nepodporovaný typ souboru. Prosím, nahrajte soubor .csv.", "error")
            return redirect(url_for("admin.kvizy_route"))

        try:
            new_quiz = Kviz(
                nazev=quiz_name,
                popis=quiz_description,
                time_limit_per_question=time_limit,
            )
            db.session.add(new_quiz)
            db.session.flush()

            stream = io.StringIO(
                file.stream.read().decode("utf-8-sig"), newline=None
            )
            csv_reader = csv.DictReader(stream)

            required_columns = {
                "otazka",
                "spravna_odpoved",
                "spatna_odpoved1",
                "spatna_odpoved2",
                "spatna_odpoved3",
            }

            questions_to_link: list[int] = []
            for row in csv_reader:
                if not required_columns.issubset(row.keys()):
                    LOGGER.warning(
                        "Přeskakuji řádek v CSV kvůli chybějícím sloupcům: %s",
                        row,
                    )
                    continue

                if not all(row.get(column) for column in required_columns):
                    LOGGER.warning(
                        "Přeskakuji řádek v CSV kvůli prázdným hodnotám: %s",
                        row,
                    )
                    continue

                question_text = row["otazka"].strip()
                existing_question = Otazka.query.filter_by(
                    otazka=question_text
                ).first()

                if existing_question is not None:
                    question_id = existing_question.id
                else:
                    new_question = Otazka(
                        otazka=question_text,
                        spravna_odpoved=row["spravna_odpoved"].strip(),
                        spatna_odpoved1=row["spatna_odpoved1"].strip(),
                        spatna_odpoved2=row["spatna_odpoved2"].strip(),
                        spatna_odpoved3=row["spatna_odpoved3"].strip(),
                        tema=row.get("tema", "Importováno").strip() or None,
                        obtiznost=_safe_int(row.get("obtiznost"), 3),
                        zdroj_url=row.get("zdroj_url", "").strip() or None,
                    )
                    db.session.add(new_question)
                    db.session.flush()
                    question_id = new_question.id

                questions_to_link.append(question_id)

            if not questions_to_link:
                raise ValueError("CSV neobsahuje žádné platné otázky k importu.")

            for index, question_id in enumerate(questions_to_link, start=1):
                link = KvizOtazky(
                    kviz_id_fk=new_quiz.kviz_id,
                    otazka_id_fk=question_id,
                    poradi=index,
                )
                db.session.add(link)

            db.session.commit()
            flash(
                f"Kvíz '{quiz_name}' úspěšně importován s {len(questions_to_link)} otázkami.",
                "success",
            )
        except Exception as exc:  # noqa: BLE001 - we want to catch all errors to rollback
            db.session.rollback()
            LOGGER.exception("Chyba při importu CSV pro kvíz '%s'", quiz_name)
            flash(f"Neočekávaná chyba při importu: {exc}", "error")

        return redirect(url_for("admin.kvizy_route"))

    return blueprint
