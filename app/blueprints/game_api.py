"""
Game API Blueprint for KvízAréna.

Handles the core gameplay logic:
- Starting a new game session.
- Submitting answers and getting results.
"""
import time
import random
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, abort
from app.database import db, Kviz, KvizOtazky, GameSession, Otazka

# Create the Blueprint
game_api_bp = Blueprint(
    'game_api',
    __name__,
    url_prefix='/api/game'  # All routes will start with /api/game
)

def _shuffle_answers(question: Otazka) -> list[dict[str, str]]:
    """Helper function to shuffle answers and return them."""
    answers = [
        # We send the text, the client should send the text back.
        # This is more robust than sending IDs (a,b,c,d).
        {"text": question.spravna_odpoved},
        {"text": question.spatna_odpoved1},
        {"text": question.spatna_odpoved2},
        {"text": question.spatna_odpoved3},
    ]
    random.shuffle(answers)
    return answers

def _get_current_question(session: GameSession) -> KvizOtazky | None:
    """Gets the current question association based on the session index."""
    current_poradi = session.current_question_index + 1
    return KvizOtazky.query.filter_by(
        kviz_id_fk=session.kviz_id_fk,
        poradi=current_poradi
    ).first()

def _get_total_questions(kviz_id: int) -> int:
    """Helper to get total question count for a quiz."""
    return db.session.query(KvizOtazky).filter_by(kviz_id_fk=kviz_id).count()

@game_api_bp.route('/quizzes', methods=['GET'])
def get_quizzes():
    """
    Returns a list of all available quizzes.
    Each quiz includes: id, nazev, popis, pocet_otazek.
    """
    quizzes = Kviz.query.all()
    
    result = []
    for kviz in quizzes:
        result.append({
            "id": kviz.kviz_id,
            "nazev": kviz.nazev,
            "popis": kviz.popis,
            "pocet_otazek": _get_total_questions(kviz.kviz_id)
        })
    
    return jsonify(result), 200

@game_api_bp.route('/start/<int:quiz_id>', methods=['POST'])
def start_game(quiz_id: int):
    """
    Starts a new game session for the given quiz.
    Returns a new session_id and the first question.
    """
    quiz = Kviz.query.get_or_404(quiz_id)
    
    # Check if quiz is active and respects scheduled time
    if not quiz.is_active:
        return jsonify({"error": "This quiz is not currently available."}), 404

    if quiz.quiz_mode == 'scheduled':
        if not quiz.start_time:
            return jsonify({"error": "This scheduled quiz has no start time set."}), 500

        # Get the current UTC time (timezone-aware)
        now_utc = datetime.now(timezone.utc)

        # Handle timezone-naive datetime from database (SQLite doesn't preserve timezone)
        quiz_start_time = quiz.start_time
        if quiz_start_time.tzinfo is None:
            # Assume stored time is UTC and make it aware
            quiz_start_time = quiz_start_time.replace(tzinfo=timezone.utc)

        if now_utc < quiz_start_time:
            # Calculate time remaining
            time_remaining = quiz_start_time - now_utc
            return jsonify({
                "error": "Quiz has not started yet.",
                "status": "scheduled",
                "starts_in_seconds": int(time_remaining.total_seconds()),
                "start_time_utc": quiz_start_time.isoformat()
            }), 403  # 403 Forbidden
    
    # Check if quiz has questions
    first_question_assoc = KvizOtazky.query.filter_by(
        kviz_id_fk=quiz.kviz_id, 
        poradi=1
    ).first()
    
    if not first_question_assoc:
        return jsonify({"error": "Quiz has no questions."}), 404

    try:
        # Create new game session
        new_session = GameSession(
            kviz_id_fk=quiz.kviz_id,
            last_question_timestamp=int(time.time())
        )
        db.session.add(new_session)
        db.session.commit() # Commit to get session_id
        
        question = first_question_assoc.otazka
        total_questions = _get_total_questions(quiz.kviz_id)
        
        return jsonify({
            "session_id": new_session.session_id,
            "quiz_name": quiz.nazev,
            "time_limit": quiz.time_limit_per_question,
            "total_questions": total_questions,
            "question": {
                "number": 1,
                "text": question.otazka,
                "answers": _shuffle_answers(question) # Send shuffled answers
            }
        }), 201 # 201 Created

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Could not start game: {e}"}), 500


@game_api_bp.route('/answer', methods=['POST'])
def submit_answer():
    """
    Submits an answer for a question in an active session.
    All logic is handled server-side for security.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    answer_text = data.get('answer_text') # We expect the text of the answer

    if not session_id or answer_text is None:
        return jsonify({"error": "Missing session_id or answer_text"}), 400

    # 1. Find the active session
    session = GameSession.query.filter_by(
        session_id=session_id, 
        is_active=True
    ).first()
    
    if not session:
        return jsonify({"error": "Invalid or expired session"}), 404

    # 2. Get the *current* question from the session
    question_assoc = _get_current_question(session)
    if not question_assoc:
        # This should not happen, but good to check
        session.is_active = False
        db.session.commit()
        return jsonify({"error": "Question sequence error or quiz finished"}), 500
    
    question = question_assoc.otazka
    quiz = session.kviz

    # 3. Check time limit
    time_limit = quiz.time_limit_per_question
    time_taken = int(time.time()) - session.last_question_timestamp
    
    is_correct = False
    
    if time_taken > time_limit:
        feedback = "Time's up!"
    else:
        # 4. Check if the answer is correct (and within time)
        if answer_text == question.spravna_odpoved:
            is_correct = True
            feedback = "Correct!"
            session.score += 1
        else:
            feedback = "Incorrect"

    # 5. Create a log entry for this answer
    log_entry = {
        "question_text": question.otazka,
        "your_answer": answer_text,
        "correct_answer": question.spravna_odpoved,
        "is_correct": is_correct,
        "feedback": feedback,
        "source_url": question.zdroj_url or ""  # Ensure it's not None
    }

    # Append the log entry (must create a new list to notify SQLAlchemy)
    new_log = list(session.answer_log)
    new_log.append(log_entry)
    session.answer_log = new_log

    # 5. Prepare for the *next* question
    session.current_question_index += 1
    session.last_question_timestamp = int(time.time())

    next_poradi = session.current_question_index + 1
    next_question_assoc = KvizOtazky.query.filter_by(
        kviz_id_fk=session.kviz_id_fk,
        poradi=next_poradi
    ).first()
    
    total_questions = _get_total_questions(quiz.kviz_id)

    # 6. Check if quiz is finished
    if not next_question_assoc:
        session.is_active = False
        db.session.commit()
        return jsonify({
            "feedback": feedback,
            "is_correct": is_correct,
            "correct_answer": question.spravna_odpoved,
            "current_score": session.score,
            "quiz_finished": True,
            "final_score": session.score,
            "total_questions": total_questions,

            # NEW KEY: Send the complete answer history
            "results_summary": session.answer_log
        })
    
    # 7. Send next question
    db.session.commit()
    next_question = next_question_assoc.otazka
    
    return jsonify({
        "feedback": feedback,
        "is_correct": is_correct,
        "correct_answer": question.spravna_odpoved,
        "current_score": session.score,
        "quiz_finished": False,
        "next_question": {
            "number": next_poradi,
            "text": next_question.otazka,
            "answers": _shuffle_answers(next_question) # Shuffle new answers
        },
        "total_questions": total_questions
    })
