"""Tests for database models and functionality."""

import pytest
from sqlalchemy import inspect
from app import create_app
from app.database import db, Otazka, Kviz, KvizOtazky, GameSession


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


def test_database_tables_created(app):
    """Test that all expected tables are created."""
    with app.app_context():
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        
        assert "otazky" in table_names
        assert "kvizy" in table_names
        assert "kviz_otazky" in table_names
        assert "game_sessions" in table_names


def test_foreign_keys_enabled(app):
    """Test that foreign key constraints are enabled."""
    with app.app_context():
        result = db.session.execute(db.text("PRAGMA foreign_keys")).fetchone()
        assert result[0] == 1, "Foreign keys should be enabled"


def test_create_question(app):
    """Test creating a question (Otazka)."""
    with app.app_context():
        question = Otazka(
            otazka="What is 2+2?",
            spravna_odpoved="4",
            spatna_odpoved1="3",
            spatna_odpoved2="5",
            spatna_odpoved3="6",
            tema="Math",
            obtiznost=1
        )
        db.session.add(question)
        db.session.commit()
        
        # Verify the question was created
        saved_question = db.session.query(Otazka).filter_by(otazka="What is 2+2?").first()
        assert saved_question is not None
        assert saved_question.spravna_odpoved == "4"
        assert saved_question.tema == "Math"
        assert saved_question.obtiznost == 1


def test_create_quiz(app):
    """Test creating a quiz (Kviz)."""
    with app.app_context():
        quiz = Kviz(
            nazev="Test Quiz",
            popis="A test quiz",
            time_limit_per_question=20
        )
        db.session.add(quiz)
        db.session.commit()
        
        # Verify the quiz was created
        saved_quiz = db.session.query(Kviz).filter_by(nazev="Test Quiz").first()
        assert saved_quiz is not None
        assert saved_quiz.popis == "A test quiz"
        assert saved_quiz.time_limit_per_question == 20


def test_quiz_questions_association(app):
    """Test the association between quizzes and questions."""
    with app.app_context():
        # Create a quiz
        quiz = Kviz(nazev="Math Quiz", popis="Basic math")
        db.session.add(quiz)
        db.session.flush()
        
        # Create questions
        q1 = Otazka(
            otazka="What is 1+1?",
            spravna_odpoved="2",
            spatna_odpoved1="1",
            spatna_odpoved2="3",
            spatna_odpoved3="4"
        )
        q2 = Otazka(
            otazka="What is 2+2?",
            spravna_odpoved="4",
            spatna_odpoved1="2",
            spatna_odpoved2="3",
            spatna_odpoved3="5"
        )
        db.session.add_all([q1, q2])
        db.session.flush()
        
        # Associate questions with quiz
        assoc1 = KvizOtazky(kviz_id_fk=quiz.kviz_id, otazka_id_fk=q1.id, poradi=1)
        assoc2 = KvizOtazky(kviz_id_fk=quiz.kviz_id, otazka_id_fk=q2.id, poradi=2)
        db.session.add_all([assoc1, assoc2])
        db.session.commit()
        
        # Verify the associations
        quiz_questions = db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz.kviz_id).order_by(KvizOtazky.poradi).all()
        assert len(quiz_questions) == 2
        assert quiz_questions[0].poradi == 1
        assert quiz_questions[1].poradi == 2


def test_game_session_creation(app):
    """Test creating a game session."""
    with app.app_context():
        # Create a quiz first
        quiz = Kviz(nazev="Session Test Quiz", popis="For testing sessions")
        db.session.add(quiz)
        db.session.flush()
        
        # Create a game session
        session = GameSession(
            session_id="test-session-123",
            kviz_id_fk=quiz.kviz_id,
            score=0,
            current_question_index=0
        )
        db.session.add(session)
        db.session.commit()
        
        # Verify the session was created
        saved_session = db.session.query(GameSession).filter_by(session_id="test-session-123").first()
        assert saved_session is not None
        assert saved_session.score == 0
        assert saved_session.is_active is True
        assert saved_session.kviz.nazev == "Session Test Quiz"


def test_foreign_key_constraint_enforced(app):
    """Test that foreign key constraints are enforced."""
    with app.app_context():
        # Try to create a GameSession with a non-existent kviz_id
        invalid_session = GameSession(
            session_id="invalid-session",
            kviz_id_fk=999999,  # Non-existent kviz
            score=0
        )
        db.session.add(invalid_session)
        
        # This should raise an IntegrityError due to foreign key constraint
        with pytest.raises(Exception) as exc_info:
            db.session.commit()
        
        assert "FOREIGN KEY constraint failed" in str(exc_info.value) or "IntegrityError" in str(exc_info.type)
        db.session.rollback()


def test_unique_constraint_question(app):
    """Test that question text must be unique."""
    with app.app_context():
        # Create first question
        q1 = Otazka(
            otazka="Unique question?",
            spravna_odpoved="Yes",
            spatna_odpoved1="No",
            spatna_odpoved2="Maybe",
            spatna_odpoved3="Unknown"
        )
        db.session.add(q1)
        db.session.commit()
        
        # Try to create another question with the same text
        q2 = Otazka(
            otazka="Unique question?",
            spravna_odpoved="Different answer",
            spatna_odpoved1="A",
            spatna_odpoved2="B",
            spatna_odpoved3="C"
        )
        db.session.add(q2)
        
        # This should raise an IntegrityError due to unique constraint
        with pytest.raises(Exception) as exc_info:
            db.session.commit()
        
        assert "UNIQUE constraint failed" in str(exc_info.value) or "IntegrityError" in str(exc_info.type)
        db.session.rollback()


def test_unique_constraint_quiz_name(app):
    """Test that quiz name must be unique."""
    with app.app_context():
        # Create first quiz
        quiz1 = Kviz(nazev="Unique Quiz Name", popis="First quiz")
        db.session.add(quiz1)
        db.session.commit()
        
        # Try to create another quiz with the same name
        quiz2 = Kviz(nazev="Unique Quiz Name", popis="Second quiz")
        db.session.add(quiz2)
        
        # This should raise an IntegrityError due to unique constraint
        with pytest.raises(Exception) as exc_info:
            db.session.commit()
        
        assert "UNIQUE constraint failed" in str(exc_info.value) or "IntegrityError" in str(exc_info.type)
        db.session.rollback()


def test_cascade_delete_quiz_questions(app):
    """Test that deleting a quiz cascades to its question associations."""
    with app.app_context():
        # Create a quiz with questions
        quiz = Kviz(nazev="Cascade Test Quiz")
        db.session.add(quiz)
        db.session.flush()
        
        question = Otazka(
            otazka="Test cascade?",
            spravna_odpoved="Yes",
            spatna_odpoved1="No",
            spatna_odpoved2="Maybe",
            spatna_odpoved3="Unknown"
        )
        db.session.add(question)
        db.session.flush()
        
        assoc = KvizOtazky(kviz_id_fk=quiz.kviz_id, otazka_id_fk=question.id, poradi=1)
        db.session.add(assoc)
        db.session.commit()
        
        quiz_id = quiz.kviz_id
        
        # Delete the quiz
        db.session.delete(quiz)
        db.session.commit()
        
        # Verify the association was also deleted
        remaining_assocs = db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz_id).all()
        assert len(remaining_assocs) == 0
