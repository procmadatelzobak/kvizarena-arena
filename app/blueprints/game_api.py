"""
Game API Blueprint for KvízAréna.

Handles the core gameplay logic:
- Starting a new game session.
- Submitting answers and getting results.
"""
import time
import random
from flask import Blueprint, jsonify, request
from app.database import db, Kviz, KvizOtazky, GameSession, Otazka

# Create the Blueprint
game_api_bp = Blueprint(
    'game_api',
    __name__,
    url_prefix='/api/game'  # All routes will start with /api/game
)

def shuffle_answers(question: Otazka) -> list[dict]:
    """Helper function to shuffle answers and return them."""
    answers = [
        {"id": "a", "text": question.spravna_odpoved},
        {"id": "b", "text": question.spatna_odpoved1},
        {"id": "c", "text": question.spatna_odpoved2},
        {"id": "d", "text": question.spatna_odpoved3},
    ]
    random.shuffle(answers)
    return answers

@game_api_bp.route('/start/<int:quiz_id>', methods=['POST'])
def start_game(quiz_id: int):
    """
    Starts a new game session for the given quiz.
    Returns a new session_id and the first question.
    """
    quiz = Kviz.query.get_or_404(quiz_id)
    
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
        
        question = Otazka.query.get(first_question_assoc.otazka_id_fk)
        
        return jsonify({
            "session_id": new_session.session_id,
            "quiz_name": quiz.nazev,
            "time_limit": quiz.time_limit_per_question,
            "total_questions": db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz.kviz_id).count(),
            "question": {
                "number": 1,
                "text": question.otazka,
                "answers": shuffle_answers(question)
            }
        }), 201 # 201 Created

    except Exception as e:
        db.session.rollback()
        # Log the error internally but don't expose details to the user
        print(f"Error starting game: {e}")  # In production, use proper logging
        return jsonify({"error": "Could not start game"}), 500


@game_api_bp.route('/answer', methods=['POST'])
def submit_answer():
    """
    Submits an answer for a question in an active session.
    All logic is handled server-side for security.
    """
    data = request.get_json()
    session_id = data.get('session_id')
    answer_text = data.get('answer_text')

    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
    
    if answer_text is None:
        return jsonify({"error": "Missing answer_text"}), 400

    # 1. Find the active session
    session = GameSession.query.filter_by(
        session_id=session_id, 
        is_active=True
    ).first()
    
    if not session:
        return jsonify({"error": "Invalid or expired session"}), 404

    # 2. Check time limit and get current question
    time_limit = session.kviz.time_limit_per_question
    time_taken = int(time.time()) - session.last_question_timestamp
    
    # 3. Get the *current* question from the session
    current_poradi = session.current_question_index + 1
    question_assoc = KvizOtazky.query.filter_by(
        kviz_id_fk=session.kviz_id_fk,
        poradi=current_poradi
    ).first()

    if not question_assoc:
        # This should not happen if logic is correct
        return jsonify({"error": "Question sequence error"}), 500
    
    question = question_assoc.otazka
    
    # 4. Evaluate answer correctness
    is_correct = False
    feedback = "Incorrect"
    
    if time_taken > time_limit:
        # Time's up - answer is incorrect regardless of content
        feedback = "Time's up!"
    elif answer_text == question.spravna_odpoved:
        # Answer is correct and within time limit
        is_correct = True
        feedback = "Correct!"
        session.score += 1

    # 5. Prepare for the *next* question
    session.current_question_index += 1
    session.last_question_timestamp = int(time.time())

    next_poradi = session.current_question_index + 1
    next_question_assoc = KvizOtazky.query.filter_by(
        kviz_id_fk=session.kviz_id_fk,
        poradi=next_poradi
    ).first()
    
    total_questions = db.session.query(KvizOtazky).filter_by(kviz_id_fk=session.kviz_id_fk).count()

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
            "total_questions": total_questions
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
            "answers": shuffle_answers(next_question)
        },
        "total_questions": total_questions
    })
