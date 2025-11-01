"""
Tests for the Game API blueprint.
"""
import pytest
import time
from app import create_app
from app.database import db, Otazka, Kviz, KvizOtazky, GameSession, User

@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key-game"
    })
    
    with app.app_context():
        db.create_all()
        
        # Create a test user
        test_user = User(nickname="test_player")
        db.session.add(test_user)
        db.session.commit()
        
        # Create a test quiz and questions
        quiz = Kviz(nazev="API Test Quiz", time_limit_per_question=10)
        q1 = Otazka(
            otazka="Q1",
            spravna_odpoved="A1",
            spatna_odpoved1="B1",
            spatna_odpoved2="C1",
            spatna_odpoved3="D1"
        )
        q2 = Otazka(
            otazka="Q2",
            spravna_odpoved="A2",
            spatna_odpoved1="B2",
            spatna_odpoved2="C2",
            spatna_odpoved3="D2"
        )
        db.session.add_all([quiz, q1, q2])
        db.session.commit()
        
        # Link questions to quiz
        assoc1 = KvizOtazky(kviz_id_fk=quiz.kviz_id, otazka_id_fk=q1.id, poradi=1)
        assoc2 = KvizOtazky(kviz_id_fk=quiz.kviz_id, otazka_id_fk=q2.id, poradi=2)
        db.session.add_all([assoc1, assoc2])
        db.session.commit()
        
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

def test_start_game(client):
    """Test starting a new game."""
    response = client.post('/api/game/start/1', 
                          json={'user_id': 1},
                          headers={'Content-Type': 'application/json'})
    assert response.status_code == 201
    
    json_data = response.get_json()
    assert 'session_id' in json_data
    assert json_data['quiz_name'] == "API Test Quiz"
    assert json_data['time_limit'] == 10
    assert json_data['total_questions'] == 2
    assert json_data['question']['number'] == 1
    assert json_data['question']['text'] == "Q1"
    assert len(json_data['question']['answers']) == 4

def test_start_game_no_questions(client, app):
    """Test starting a game on a quiz with no questions."""
    with app.app_context():
        empty_quiz = Kviz(nazev="Empty Quiz")
        db.session.add(empty_quiz)
        db.session.commit()
        quiz_id = empty_quiz.kviz_id
        
    response = client.post(f'/api/game/start/{quiz_id}')
    assert response.status_code == 404
    assert response.get_json()['error'] == "Quiz has no questions."

def test_submit_answer_correct(client):
    """Test submitting a correct answer."""
    # 1. Start game
    response_start = client.post('/api/game/start/1', json={'user_id': 1}, headers={'Content-Type': 'application/json'})
    session_id = response_start.get_json()['session_id']
    
    # 2. Submit correct answer
    response_answer = client.post('/api/game/answer', json={
        "session_id": session_id,
        "user_id": 1,
        "answer_text": "A1"
    })
    
    assert response_answer.status_code == 200
    json_data = response_answer.get_json()
    assert json_data['is_correct'] is True
    assert json_data['feedback'] == "Correct!"
    assert json_data['current_score'] == 1
    assert json_data['quiz_finished'] is False
    assert json_data['next_question']['number'] == 2
    assert json_data['next_question']['text'] == "Q2"

def test_submit_answer_incorrect(client):
    """Test submitting an incorrect answer."""
    # 1. Start game
    response_start = client.post('/api/game/start/1', json={'user_id': 1}, headers={'Content-Type': 'application/json'})
    session_id = response_start.get_json()['session_id']
    
    # 2. Submit incorrect answer
    response_answer = client.post('/api/game/answer', json={
        "session_id": session_id,
        "user_id": 1,
        "answer_text": "Wrong Answer"
    })
    
    assert response_answer.status_code == 200
    json_data = response_answer.get_json()
    assert json_data['is_correct'] is False
    assert json_data['feedback'] == "Incorrect"
    assert json_data['current_score'] == 0
    assert json_data['next_question']['number'] == 2

def test_submit_answer_time_limit(client, app):
    """Test submitting an answer after the time limit."""
    # 1. Start game
    response_start = client.post('/api/game/start/1', json={'user_id': 1}, headers={'Content-Type': 'application/json'})
    session_id = response_start.get_json()['session_id']
    
    # 2. Manually update timestamp in DB to simulate time running out
    with app.app_context():
        session = db.session.get(GameSession, session_id)
        session.last_question_timestamp = int(time.time()) - 15 # 15s ago
        db.session.commit()
        
    # 3. Submit answer (even if correct, it's too late)
    response_answer = client.post('/api/game/answer', json={
        "session_id": session_id,
        "user_id": 1,
        "answer_text": "A1"
    })
    
    assert response_answer.status_code == 200
    json_data = response_answer.get_json()
    assert json_data['is_correct'] is False
    assert json_data['feedback'] == "Time's up!"
    assert json_data['current_score'] == 0 # No points for being late
    assert json_data['next_question']['number'] == 2

def test_game_completion(client):
    """Test submitting the last answer and finishing the game."""
    # 1. Start game
    response_start = client.post('/api/game/start/1', json={'user_id': 1}, headers={'Content-Type': 'application/json'})
    session_id = response_start.get_json()['session_id']
    
    # 2. Submit answer for Q1
    client.post('/api/game/answer', json={
        "session_id": session_id,
        "user_id": 1,
        "answer_text": "A1" # Correct
    })
    
    # 3. Submit answer for Q2 (last question)
    response_final = client.post('/api/game/answer', json={
        "session_id": session_id,
        "user_id": 1,
        "answer_text": "Wrong Answer" # Incorrect
    })
    
    assert response_final.status_code == 200
    json_data = response_final.get_json()
    assert json_data['is_correct'] is False
    assert json_data['quiz_finished'] is True
    assert json_data['final_score'] == 1 # 1 point from Q1
    assert json_data['total_questions'] == 2
    assert 'next_question' not in json_data

def test_submit_answer_invalid_session(client):
    """Test submitting an answer with an invalid session ID."""
    response = client.post('/api/game/answer', json={
        "session_id": "non-existent-session-id",
        "answer_text": "A1"
    })
    assert response.status_code == 404
    assert response.get_json()['error'] == "Invalid or expired session"

def test_get_quizzes(client, app):
    """Test getting all available quizzes."""
    response = client.get('/api/game/quizzes')
    assert response.status_code == 200
    
    json_data = response.get_json()
    assert isinstance(json_data, list)
    assert len(json_data) == 1  # We have one quiz in the test fixture
    
    quiz = json_data[0]
    assert quiz['id'] == 1
    assert quiz['nazev'] == "API Test Quiz"
    assert quiz['popis'] is None
    assert quiz['pocet_otazek'] == 2

def test_get_quizzes_empty(client, app):
    """Test getting quizzes when none exist."""
    # Remove the test quiz
    with app.app_context():
        db.session.query(KvizOtazky).delete()
        db.session.query(Kviz).delete()
        db.session.commit()
    
    response = client.get('/api/game/quizzes')
    assert response.status_code == 200
    assert response.get_json() == []

