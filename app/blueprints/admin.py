"""
Admin blueprint for KvízAréna.

Handles quiz management, deletion, and the crucial function
for importing quizzes from CSV (exported from Vševěd).
"""
import csv
import io
import logging
from datetime import datetime
from flask import (
    Blueprint, render_template, request,
    flash, redirect, url_for
)
from werkzeug.utils import secure_filename
from app.database import db, Otazka, Kviz, KvizOtazky, User, GameResult
from sqlalchemy import func as sqlalchemy_func
from app.auth import admin_required

# Create the Blueprint
admin_bp = Blueprint(
    'admin',
    __name__,
    url_prefix='/admin',  # All routes in this blueprint will start with /admin
    template_folder='../templates/admin' # Templates will be in app/templates/admin/
)

@admin_bp.before_request
@admin_required
def before_request():
    """Protect all admin routes."""
    pass

@admin_bp.route('/kvizy', methods=['GET'])
def kvizy_route():
    """
    Displays the list of quizzes.
    (Adapted from Vševěd and converted to SQLAlchemy)
    """
    # GET request only - quiz creation removed
    all_quizzes = Kviz.query.order_by(Kviz.nazev).all()
    # To display question counts, we fetch them efficiently
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
    Deletes a quiz. (Adapted from Vševěd)
    Thanks to 'cascade' in the model, this also deletes entries in KvizOtazky.
    """
    quiz_to_delete = Kviz.query.get_or_404(kviz_id)
    try:
        db.session.delete(quiz_to_delete)
        db.session.commit()
        flash(f"Quiz '{quiz_to_delete.nazev}' was successfully deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting quiz: {e}", "error")
    
    return redirect(url_for('admin.kvizy_route'))

@admin_bp.route('/kviz/import', methods=['POST'])
def import_quiz_csv():
    """
    Processes an uploaded CSV file and creates a new quiz.
    (Adapted from Vševěd and converted to SQLAlchemy)
    """
    quiz_name = request.form.get('quiz_name', '').strip()
    quiz_description = request.form.get('quiz_description', '').strip()
    time_limit = request.form.get('time_limit', 15)

    quiz_mode = request.form.get('quiz_mode', 'on_demand')
    start_time_str = request.form.get('start_time', '')

    start_time_obj = None
    if quiz_mode == 'scheduled' and start_time_str:
        try:
            start_time_obj = datetime.fromisoformat(start_time_str)
        except ValueError:
            flash("Invalid datetime format for Start Time.", "error")
            return redirect(url_for('admin.kvizy_route'))

    file = request.files.get('csv_file')

    if not quiz_name or not file or file.filename == '':
        flash("Quiz name and CSV file are required.", "error")
        return redirect(url_for('admin.kvizy_route'))

    # Check if quiz name already exists
    if Kviz.query.filter_by(nazev=quiz_name).first():
        flash(f"A quiz with the name '{quiz_name}' already exists. Choose another name.", "error")
        return redirect(url_for('admin.kvizy_route'))

    if not file.filename.lower().endswith('.csv'):
        flash("Unsupported file type. Please upload a .csv file.", "error")
        return redirect(url_for('admin.kvizy_route'))

    try:
        # 1. Create the new quiz
        allow_retakes = request.form.get('allow_retakes') == 'on'

        new_quiz = Kviz(
            nazev=quiz_name,
            popis=quiz_description,
            time_limit_per_question=int(time_limit),
            quiz_mode=quiz_mode,
            start_time=start_time_obj,
            is_active=request.form.get('is_active') == 'on',  # Checkbox
            allow_retakes=allow_retakes
        )
        db.session.add(new_quiz)
        db.session.commit()  # Commit to get the new_quiz.kviz_id

        # 2. Process the CSV
        # Use UTF-8-SIG to handle potential BOM from Excel
        stream = io.StringIO(file.stream.read().decode("UTF-8-SIG"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        required_columns = ['otazka', 'spravna_odpoved', 'spatna_odpoved1', 'spatna_odpoved2', 'spatna_odpoved3']
        
        questions_to_link = []
        question_ids_in_this_quiz = set()

        for row in csv_reader:
            if not all(col in row and row[col] for col in required_columns):
                logging.warning(f"Skipping CSV row due to missing data: {row}")
                continue

            # 3. Find the question in the DB or create it
            otazka_text = row['otazka'].strip()
            existing_question = Otazka.query.filter_by(otazka=otazka_text).first()
            
            if existing_question:
                question_id = existing_question.id
            else:
                # Question doesn't exist, create it
                new_question = Otazka(
                    otazka=otazka_text,
                    spravna_odpoved=row['spravna_odpoved'].strip(),
                    spatna_odpoved1=row['spatna_odpoved1'].strip(),
                    spatna_odpoved2=row['spatna_odpoved2'].strip(),
                    spatna_odpoved3=row['spatna_odpoved3'].strip(),
                    tema=row.get('tema', 'Imported').strip(),
                    obtiznost=int(row.get('obtiznost', 3)),
                    zdroj_url=row.get('zdroj_url', '').strip()
                )
                db.session.add(new_question)
                db.session.commit() # Commit to get the ID
                question_id = new_question.id
            
            # Check if we have already added this question to this specific quiz
            if question_id not in question_ids_in_this_quiz:
                questions_to_link.append(question_id)
                question_ids_in_this_quiz.add(question_id)
            else:
                # We've already seen this question in this CSV, skip it
                logging.warning(f"Skipping duplicate question in CSV: {otazka_text}")

        # 4. Link all questions to the quiz with correct ordering
        for index, q_id in enumerate(questions_to_link):
            association = KvizOtazky(
                kviz_id_fk=new_quiz.kviz_id,
                otazka_id_fk=q_id,
                poradi=index + 1
            )
            db.session.add(association)
        
        db.session.commit()
        flash(f"Quiz '{quiz_name}' successfully imported with {len(questions_to_link)} questions.", "success")
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error during CSV import: {e}", exc_info=True)
        flash(f"An unexpected error occurred during import: {e}", "error")
        # If import failed, delete the quiz entry we just created
        if 'new_quiz' in locals() and new_quiz.kviz_id:
            db.session.delete(new_quiz)
            db.session.commit()

    return redirect(url_for('admin.kvizy_route'))

@admin_bp.route('/kviz/stats/<int:kviz_id>')
def quiz_stats(kviz_id: int):
    """Displays detailed statistics for a specific quiz."""
    quiz = Kviz.query.get_or_404(kviz_id)
    results = GameResult.query.filter_by(kviz_id_fk=kviz_id).all()

    total_plays = len(results)
    avg_score = 0
    if total_plays > 0:
        avg_score = db.session.query(sqlalchemy_func.avg(GameResult.score)).filter_by(kviz_id_fk=kviz_id).scalar()

    # Aggregate per-question stats (this is complex)
    question_stats = {}
    # Initialize with all questions from the quiz
    for assoc in quiz.otazky_v_kvizu:
        q = assoc.otazka
        question_stats[q.id] = {
            "text": q.otazka,
            "correct": q.spravna_odpoved,
            "answers": {
                q.spravna_odpoved: 0,
                q.spatna_odpoved1: 0,
                q.spatna_odpoved2: 0,
                q.spatna_odpoved3: 0,
            }
        }

    # Aggregate data from all results
    for result in results:
        for log in result.answer_log:
            # Find the question in our stats dict
            q_text = log.get('question_text')
            q_stat = next((qs for qs in question_stats.values() if qs['text'] == q_text), None)

            if q_stat:
                user_answer = log.get('your_answer')
                if user_answer in q_stat['answers']:
                    q_stat['answers'][user_answer] += 1
                elif user_answer == "": # Handle timeout
                    pass # Or add a 'timeout' counter

    return render_template('stats.html', 
                           quiz=quiz, 
                           total_plays=total_plays, 
                           avg_score=avg_score,
                           question_stats=question_stats.values())
