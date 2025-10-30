"""
Admin blueprint pro KvízArénu.

Obsluhuje správu kvízů, mazání a klíčovou funkci
pro import kvízů z CSV (exportovaných z Vševěda).
"""
import csv
import io
import logging

from flask import (
    Blueprint, render_template, request,
    flash, redirect, url_for
)

from app.database import db, Otazka, Kviz, KvizOtazky

LOGGER = logging.getLogger(__name__)

# Vytvoření Blueprintu
admin_bp = Blueprint(
    'admin',
    __name__,
    url_prefix='/admin',  # Všechny routy v tomto blueprintu budou začínat /admin
    template_folder='../templates/admin' # Šablony pro tento blueprint budou v app/templates/admin/
)

@admin_bp.route('/kvizy', methods=['GET', 'POST'])
def kvizy_route():
    """
    Zobrazí seznam kvízů a zpracuje vytvoření nového.
    (Převzato z Vševěda a upraveno pro SQLAlchemy)
    """
    if request.method == 'POST':
        nazev = request.form.get('quiz_name')
        popis = request.form.get('quiz_description', '')
        time_limit = request.form.get('time_limit', 15)

        if not nazev:
            flash("Název kvízu nesmí být prázdný.", "warning")
        else:
            # Zkontrolujeme, zda kvíz již neexistuje
            existing_quiz = Kviz.query.filter_by(nazev=nazev).first()
            if existing_quiz:
                flash(f"Kvíz s názvem '{nazev}' již existuje.", "error")
            else:
                try:
                    new_quiz = Kviz(
                        nazev=nazev,
                        popis=popis,
                        time_limit_per_question=int(time_limit)
                    )
                    db.session.add(new_quiz)
                    db.session.commit()
                    flash(f"Kvíz '{nazev}' byl úspěšně vytvořen.", "success")
                    return redirect(url_for('admin.kvizy_route'))
                except Exception as e:  # noqa: BLE001 - chceme zachytit všechny chyby kvůli rollbacku
                    db.session.rollback()
                    LOGGER.exception("Došlo k chybě při vytváření kvízu '%s'", nazev)
                    flash(f"Došlo k chybě při vytváření kvízu: {e}", "error")

    # GET request
    all_quizzes = Kviz.query.order_by(Kviz.nazev).all()
    # Pro každý kvíz spočítáme otázky (efektivněji)
    quizzes_with_counts = []
    for quiz in all_quizzes:
        count = db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz.kviz_id).count()
        quizzes_with_counts.append({
            "kviz": quiz,
            "pocet_otazek": count
        })

    return render_template('kvizy.html', quizzes_with_counts=quizzes_with_counts)

@admin_bp.route('/kviz/delete/<int:kviz_id>', methods=['POST'])
def delete_quiz_route(kviz_id: int):
    """
    Smaže kvíz. (Převzato z Vševěda a upraveno pro SQLAlchemy)
    Díky 'cascade' v modelu se smažou i vazby v KvizOtazky.
    """
    quiz_to_delete = Kviz.query.get_or_404(kviz_id)
    try:
        db.session.delete(quiz_to_delete)
        db.session.commit()
        flash(f"Kvíz '{quiz_to_delete.nazev}' byl úspěšně smazán.", "success")
    except Exception as e:  # noqa: BLE001 - chceme zachytit všechny chyby kvůli rollbacku
        db.session.rollback()
        LOGGER.exception("Chyba při mazání kvízu %s", kviz_id)
        flash(f"Chyba při mazání kvízu: {e}", "error")
    
    return redirect(url_for('admin.kvizy_route'))

@admin_bp.route('/kviz/import', methods=['POST'])
def import_quiz_csv():
    """
    Zpracuje nahraný CSV soubor a vytvoří nový kvíz.
    (Převzato z Vševěda a upraveno pro SQLAlchemy)
    """
    quiz_name = request.form.get('quiz_name', '').strip()
    quiz_description = request.form.get('quiz_description', '').strip()
    time_limit = request.form.get('time_limit', 15)
    file = request.files.get('csv_file')

    if not quiz_name or not file or file.filename == '':
        flash("Název kvízu a CSV soubor jsou povinné.", "error")
        return redirect(url_for('admin.kvizy_route'))

    # Zkontrolujeme, zda kvíz již neexistuje
    if Kviz.query.filter_by(nazev=quiz_name).first():
        flash(f"Kvíz s názvem '{quiz_name}' již existuje. Zvolte jiný název.", "error")
        return redirect(url_for('admin.kvizy_route'))

    if not file.filename.lower().endswith('.csv'):
        flash("Nepodporovaný typ souboru. Prosím, nahrajte soubor .csv.", "error")
        return redirect(url_for('admin.kvizy_route'))

    try:
        # 1. Vytvoříme nový kvíz
        new_quiz = Kviz(
            nazev=quiz_name,
            popis=quiz_description,
            time_limit_per_question=int(time_limit)
        )
        db.session.add(new_quiz)
        db.session.commit()  # Musíme commitnout, abychom získali new_quiz.kviz_id

        # 2. Zpracujeme CSV
        stream = io.StringIO(file.stream.read().decode("UTF-8-SIG"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        required_columns = ['otazka', 'spravna_odpoved', 'spatna_odpoved1', 'spatna_odpoved2', 'spatna_odpoved3']
        
        questions_to_link = []

        for row in csv_reader:
            if not all(col in row and row[col] for col in required_columns):
                LOGGER.warning("Přeskakuji řádek v CSV kvůli chybějícím datům: %s", row)
                continue

            # 3. Najdeme otázku v DB nebo ji vytvoříme
            otazka_text = row['otazka'].strip()
            existing_question = Otazka.query.filter_by(otazka=otazka_text).first()
            
            if existing_question:
                question_id = existing_question.id
            else:
                # Otázka neexistuje, vytvoříme ji
                new_question = Otazka(
                    otazka=otazka_text,
                    spravna_odpoved=row['spravna_odpoved'].strip(),
                    spatna_odpoved1=row['spatna_odpoved1'].strip(),
                    spatna_odpoved2=row['spatna_odpoved2'].strip(),
                    spatna_odpoved3=row['spatna_odpoved3'].strip(),
                    tema=row.get('tema', 'Importováno').strip(),
                    obtiznost=int(row.get('obtiznost', 3)),
                    zdroj_url=row.get('zdroj_url', '').strip()
                )
                db.session.add(new_question)
                db.session.commit() # Commitneme, abychom dostali ID
                question_id = new_question.id
            
            questions_to_link.append(question_id)

        # 4. Přidáme všechny otázky do kvízu se správným pořadím
        for index, q_id in enumerate(questions_to_link):
            vazba = KvizOtazky(
                kviz_id_fk=new_quiz.kviz_id,
                otazka_id_fk=q_id,
                poradi=index + 1
            )
            db.session.add(vazba)
        
        db.session.commit()
        flash(f"Kvíz '{quiz_name}' úspěšně importován s {len(questions_to_link)} otázkami.", "success")
        
    except Exception as e:  # noqa: BLE001 - chceme zachytit všechny chyby kvůli rollbacku
        db.session.rollback()
        LOGGER.exception("Chyba při importu CSV: %s", e)
        flash(f"Neočekávaná chyba při importu: {e}", "error")
        # Pokud se import pokazil, smažeme i právě vytvořený kvíz
        if 'new_quiz' in locals() and new_quiz.kviz_id:
            try:
                db.session.delete(new_quiz)
                db.session.commit()
            except Exception:  # noqa: BLE001 - chceme zachytit všechny chyby kvůli rollbacku
                db.session.rollback()

    return redirect(url_for('admin.kvizy_route'))
