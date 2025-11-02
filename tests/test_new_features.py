"""
Tests for the new features: Results Summary and Scheduled Quizzes.
"""
import pytest
import time
from datetime import datetime, timezone, timedelta
from app import create_app
from app.database import db, Otazka, Kviz, KvizOtazky, GameSession, User

@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key-new-features"
    })
    
    with app.app_context():
        db.create_all()
        # Create a test user for all tests
        test_user = User(username="test_player", name="Test Player")
        db.session.add(test_user)
        db.session.commit()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

@pytest.fixture
def logged_in_client(app):
    """A client that is logged in as a regular user."""
    with app.app_context():
        # Get the test user created in app fixture
        user = User.query.filter_by(username="test_player").first()
        user_id = user.id

    with app.test_client() as client:
        # Set the user ID in the session
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
        yield client

def create_test_quiz(app, quiz_mode='on_demand', start_time=None, is_active=True):
    """Helper to create a test quiz with questions."""
    with app.app_context():
        quiz = Kviz(
            nazev=f"Test Quiz {quiz_mode}",
            time_limit_per_question=10,
            quiz_mode=quiz_mode,
            start_time=start_time,
            is_active=is_active
        )
        q1 = Otazka(
            otazka="Q1",
            spravna_odpoved="A1",
            spatna_odpoved1="B1",
            spatna_odpoved2="C1",
            spatna_odpoved3="D1",
            zdroj_url="http://example.com/q1"
        )
        q2 = Otazka(
            otazka="Q2",
            spravna_odpoved="A2",
            spatna_odpoved1="B2",
            spatna_odpoved2="C2",
            spatna_odpoved3="D2",
            zdroj_url="http://example.com/q2"
        )
        db.session.add_all([quiz, q1, q2])
        db.session.commit()
        
        # Link questions to quiz
        assoc1 = KvizOtazky(kviz_id_fk=quiz.kviz_id, otazka_id_fk=q1.id, poradi=1)
        assoc2 = KvizOtazky(kviz_id_fk=quiz.kviz_id, otazka_id_fk=q2.id, poradi=2)
        db.session.add_all([assoc1, assoc2])
        db.session.commit()
        
        return quiz.kviz_id


# Tests for Results Summary Feature

def test_answer_log_in_session(logged_in_client, app):
    """Test that answer_log is created and populated."""
    quiz_id = create_test_quiz(app)
    
    # Start game
    response = logged_in_client.post(f'/api/game/start/{quiz_id}')
    session_id = response.get_json()['session_id']
    
    # Submit first answer
    logged_in_client.post('/api/game/answer', json={
        "session_id": session_id,
        
        "answer_text": "A1"  # Correct
    })
    
    # Check session in DB
    with app.app_context():
        session = db.session.get(GameSession, session_id)
        assert len(session.answer_log) == 1
        assert session.answer_log[0]['question_text'] == "Q1"
        assert session.answer_log[0]['your_answer'] == "A1"
        assert session.answer_log[0]['correct_answer'] == "A1"
        assert session.answer_log[0]['is_correct'] is True
        assert session.answer_log[0]['source_url'] == "http://example.com/q1"


def test_results_summary_returned(logged_in_client, app):
    """Test that results_summary is returned when quiz finishes."""
    quiz_id = create_test_quiz(app)
    
    # Start game
    response = logged_in_client.post(f'/api/game/start/{quiz_id}')
    session_id = response.get_json()['session_id']
    
    # Submit first answer (correct)
    logged_in_client.post('/api/game/answer', json={
        "session_id": session_id,
        
        "answer_text": "A1"
    })
    
    # Submit second answer (incorrect) - last question
    response_final = logged_in_client.post('/api/game/answer', json={
        "session_id": session_id,
        
        "answer_text": "Wrong"
    })
    
    json_data = response_final.get_json()
    assert json_data['quiz_finished'] is True
    assert 'results_summary' in json_data
    assert len(json_data['results_summary']) == 2
    
    # Check first answer in summary
    assert json_data['results_summary'][0]['question_text'] == "Q1"
    assert json_data['results_summary'][0]['your_answer'] == "A1"
    assert json_data['results_summary'][0]['is_correct'] is True
    assert json_data['results_summary'][0]['source_url'] == "http://example.com/q1"
    
    # Check second answer in summary
    assert json_data['results_summary'][1]['question_text'] == "Q2"
    assert json_data['results_summary'][1]['your_answer'] == "Wrong"
    assert json_data['results_summary'][1]['is_correct'] is False
    assert json_data['results_summary'][1]['source_url'] == "http://example.com/q2"


# Tests for Scheduled Quizzes Feature

def test_inactive_quiz_not_available(logged_in_client, app):
    """Test that inactive quizzes cannot be started."""
    quiz_id = create_test_quiz(app, is_active=False)
    
    response = logged_in_client.post(f'/api/game/start/{quiz_id}')
    assert response.status_code == 404
    assert response.get_json()['error'] == "This quiz is not currently available."


def test_scheduled_quiz_before_start_time(logged_in_client, app):
    """Test that scheduled quiz cannot be started before its start time."""
    # Create a quiz that starts 1 hour in the future
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    quiz_id = create_test_quiz(app, quiz_mode='scheduled', start_time=future_time)
    
    response = logged_in_client.post(f'/api/game/start/{quiz_id}')
    assert response.status_code == 403
    
    json_data = response.get_json()
    assert json_data['error'] == "Quiz has not started yet."
    assert json_data['status'] == "scheduled"
    assert 'starts_in_seconds' in json_data
    assert json_data['starts_in_seconds'] > 3500  # About 1 hour
    assert 'start_time_utc' in json_data


def test_scheduled_quiz_after_start_time(logged_in_client, app):
    """Test that scheduled quiz can be started after its start time."""
    # Create a quiz that started 1 hour ago
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    quiz_id = create_test_quiz(app, quiz_mode='scheduled', start_time=past_time)
    
    response = logged_in_client.post(f'/api/game/start/{quiz_id}')
    assert response.status_code == 201
    
    json_data = response.get_json()
    assert 'session_id' in json_data
    assert json_data['quiz_name'] == "Test Quiz scheduled"


def test_on_demand_quiz_always_available(logged_in_client, app):
    """Test that on-demand quizzes can always be started."""
    quiz_id = create_test_quiz(app, quiz_mode='on_demand')
    
    response = logged_in_client.post(f'/api/game/start/{quiz_id}')
    assert response.status_code == 201
    
    json_data = response.get_json()
    assert 'session_id' in json_data


def test_scheduled_quiz_without_start_time(logged_in_client, app):
    """Test that scheduled quiz without start_time returns error."""
    quiz_id = create_test_quiz(app, quiz_mode='scheduled', start_time=None)
    
    response = logged_in_client.post(f'/api/game/start/{quiz_id}')
    assert response.status_code == 500
    assert response.get_json()['error'] == "This scheduled quiz has no start time set."


# Tests for Database Model

def test_kviz_new_fields(app):
    """Test that new Kviz fields are properly stored."""
    with app.app_context():
        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        quiz = Kviz(
            nazev="Model Test Quiz",
            quiz_mode="scheduled",
            start_time=start_time,
            is_active=False
        )
        db.session.add(quiz)
        db.session.commit()
        
        # Retrieve and verify
        retrieved = Kviz.query.filter_by(nazev="Model Test Quiz").first()
        assert retrieved.quiz_mode == "scheduled"
        # SQLite doesn't preserve timezone, so compare without timezone
        assert retrieved.start_time.replace(tzinfo=timezone.utc) == start_time
        assert retrieved.is_active is False


def test_game_session_answer_log_default(app):
    """Test that answer_log has default empty list."""
    with app.app_context():
        # User should already exist from the fixture
        user = User.query.get(1)
        
        quiz = Kviz(nazev="Session Test Quiz")
        db.session.add(quiz)
        db.session.commit()
        
        session = GameSession(kviz_id_fk=quiz.kviz_id, user_id_fk=user.id)
        db.session.add(session)
        db.session.commit()
        
        # Retrieve and verify
        retrieved = db.session.get(GameSession, session.session_id)
        assert retrieved.answer_log == []
        assert isinstance(retrieved.answer_log, list)
