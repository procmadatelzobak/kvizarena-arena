"""Tests for admin blueprint functionality."""

import io
import pytest
from app import create_app
from app.database import db, Otazka, Kviz, KvizOtazky


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
        "SECRET_KEY": "test-secret-key"  # Required for sessions and flash messages
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


def test_admin_blueprint_registered(app):
    """Test that admin blueprint is registered."""
    assert "admin" in app.blueprints


def test_kvizy_route_get(client, app):
    """Test GET request to /admin/kvizy route."""
    with app.app_context():
        # Create a sample quiz
        quiz = Kviz(nazev="Test Quiz", popis="Test description", time_limit_per_question=20)
        db.session.add(quiz)
        db.session.commit()
    
    response = client.get('/admin/kvizy')
    assert response.status_code == 200
    # Note: This will fail if template is missing, but that's expected for now


def test_kvizy_route_post_create_quiz(client, app):
    """Test POST request to /admin/kvizy to create a new quiz."""
    response = client.post('/admin/kvizy', data={
        'quiz_name': 'New Test Quiz',
        'quiz_description': 'A new quiz for testing',
        'time_limit': 30
    }, follow_redirects=True)
    
    with app.app_context():
        quiz = Kviz.query.filter_by(nazev='New Test Quiz').first()
        assert quiz is not None
        assert quiz.popis == 'A new quiz for testing'
        assert quiz.time_limit_per_question == 30


def test_kvizy_route_post_empty_name(client, app):
    """Test POST with empty quiz name returns error."""
    response = client.post('/admin/kvizy', data={
        'quiz_name': '',
        'quiz_description': 'Description',
        'time_limit': 15
    }, follow_redirects=True)
    
    with app.app_context():
        # Verify no quiz was created
        count = db.session.query(Kviz).count()
        assert count == 0


def test_kvizy_route_post_duplicate_name(client, app):
    """Test POST with duplicate quiz name returns error."""
    with app.app_context():
        # Create initial quiz
        quiz = Kviz(nazev='Duplicate Quiz', popis='First')
        db.session.add(quiz)
        db.session.commit()
    
    # Try to create another quiz with same name
    response = client.post('/admin/kvizy', data={
        'quiz_name': 'Duplicate Quiz',
        'quiz_description': 'Second',
        'time_limit': 15
    }, follow_redirects=True)
    
    with app.app_context():
        # Verify only one quiz exists
        count = db.session.query(Kviz).filter_by(nazev='Duplicate Quiz').count()
        assert count == 1


def test_delete_quiz_route(client, app):
    """Test POST request to /admin/kviz/delete/<id>."""
    with app.app_context():
        # Create a quiz to delete
        quiz = Kviz(nazev='Quiz to Delete', popis='Will be deleted')
        db.session.add(quiz)
        db.session.commit()
        quiz_id = quiz.kviz_id
    
    # Delete the quiz
    response = client.post(f'/admin/kviz/delete/{quiz_id}', follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        # Verify quiz was deleted
        deleted_quiz = Kviz.query.get(quiz_id)
        assert deleted_quiz is None


def test_delete_quiz_with_questions(client, app):
    """Test deleting a quiz also deletes its question associations."""
    with app.app_context():
        # Create quiz and question
        quiz = Kviz(nazev='Quiz with Questions', popis='Has questions')
        question = Otazka(
            otazka='Test question?',
            spravna_odpoved='Yes',
            spatna_odpoved1='No',
            spatna_odpoved2='Maybe',
            spatna_odpoved3='Unknown'
        )
        db.session.add_all([quiz, question])
        db.session.flush()
        
        # Associate question with quiz
        assoc = KvizOtazky(kviz_id_fk=quiz.kviz_id, otazka_id_fk=question.id, poradi=1)
        db.session.add(assoc)
        db.session.commit()
        
        quiz_id = quiz.kviz_id
    
    # Delete the quiz
    response = client.post(f'/admin/kviz/delete/{quiz_id}', follow_redirects=True)
    
    with app.app_context():
        # Verify quiz was deleted
        assert Kviz.query.get(quiz_id) is None
        # Verify association was also deleted (cascade)
        assert db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz_id).count() == 0


def test_import_csv_basic(client, app):
    """Test basic CSV import functionality."""
    csv_content = """otazka,spravna_odpoved,spatna_odpoved1,spatna_odpoved2,spatna_odpoved3,tema,obtiznost
What is 2+2?,4,3,5,6,Math,1
What is the capital of France?,Paris,London,Berlin,Madrid,Geography,2"""
    
    data = {
        'quiz_name': 'Imported Quiz',
        'quiz_description': 'Imported from CSV',
        'time_limit': 25,
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv')
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        # Verify quiz was created
        quiz = Kviz.query.filter_by(nazev='Imported Quiz').first()
        assert quiz is not None
        assert quiz.popis == 'Imported from CSV'
        assert quiz.time_limit_per_question == 25
        
        # Verify questions were created
        questions = db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz.kviz_id).order_by(KvizOtazky.poradi).all()
        assert len(questions) == 2
        assert questions[0].poradi == 1
        assert questions[1].poradi == 2
        
        # Verify question content
        q1 = Otazka.query.get(questions[0].otazka_id_fk)
        assert q1.otazka == 'What is 2+2?'
        assert q1.spravna_odpoved == '4'
        assert q1.tema == 'Math'
        assert q1.obtiznost == 1


def test_import_csv_utf8_sig(client, app):
    """Test CSV import with UTF-8-SIG encoding (BOM)."""
    # Create CSV with BOM
    csv_content = "\ufeffotazka,spravna_odpoved,spatna_odpoved1,spatna_odpoved2,spatna_odpoved3\nTest question?,Answer,Wrong1,Wrong2,Wrong3"
    
    data = {
        'quiz_name': 'BOM Quiz',
        'quiz_description': 'With BOM',
        'time_limit': 15,
        'csv_file': (io.BytesIO(csv_content.encode('utf-8-sig')), 'test_bom.csv')
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        quiz = Kviz.query.filter_by(nazev='BOM Quiz').first()
        assert quiz is not None


def test_import_csv_existing_question(client, app):
    """Test CSV import with questions that already exist in database."""
    with app.app_context():
        # Create existing question
        existing_q = Otazka(
            otazka='Existing question?',
            spravna_odpoved='Yes',
            spatna_odpoved1='No',
            spatna_odpoved2='Maybe',
            spatna_odpoved3='Unknown'
        )
        db.session.add(existing_q)
        db.session.commit()
        existing_q_id = existing_q.id
    
    csv_content = """otazka,spravna_odpoved,spatna_odpoved1,spatna_odpoved2,spatna_odpoved3
Existing question?,Yes,No,Maybe,Unknown
New question?,New answer,Wrong1,Wrong2,Wrong3"""
    
    data = {
        'quiz_name': 'Mixed Quiz',
        'quiz_description': 'Has existing and new questions',
        'time_limit': 15,
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'mixed.csv')
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    
    with app.app_context():
        quiz = Kviz.query.filter_by(nazev='Mixed Quiz').first()
        assert quiz is not None
        
        # Verify both questions are linked
        questions = db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz.kviz_id).order_by(KvizOtazky.poradi).all()
        assert len(questions) == 2
        
        # First question should be the existing one
        assert questions[0].otazka_id_fk == existing_q_id
        
        # Verify only one question with that text exists (no duplicate)
        count = db.session.query(Otazka).filter_by(otazka='Existing question?').count()
        assert count == 1


def test_import_csv_no_file(client, app):
    """Test CSV import without file returns error."""
    data = {
        'quiz_name': 'No File Quiz',
        'quiz_description': 'Should fail',
        'time_limit': 15
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        # Verify no quiz was created
        quiz = Kviz.query.filter_by(nazev='No File Quiz').first()
        assert quiz is None


def test_import_csv_empty_name(client, app):
    """Test CSV import without quiz name returns error."""
    csv_content = "otazka,spravna_odpoved,spatna_odpoved1,spatna_odpoved2,spatna_odpoved3\nQ?,A,B,C,D"
    
    data = {
        'quiz_name': '   ',  # Empty/whitespace name
        'quiz_description': 'No name',
        'time_limit': 15,
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv')
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    
    with app.app_context():
        # Verify no quiz was created
        count = db.session.query(Kviz).count()
        assert count == 0


def test_import_csv_duplicate_quiz_name(client, app):
    """Test CSV import with duplicate quiz name returns error."""
    with app.app_context():
        # Create existing quiz
        quiz = Kviz(nazev='Existing Quiz Name')
        db.session.add(quiz)
        db.session.commit()
    
    csv_content = "otazka,spravna_odpoved,spatna_odpoved1,spatna_odpoved2,spatna_odpoved3\nQ?,A,B,C,D"
    
    data = {
        'quiz_name': 'Existing Quiz Name',
        'quiz_description': 'Duplicate',
        'time_limit': 15,
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv')
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    
    with app.app_context():
        # Verify only one quiz with that name exists
        count = db.session.query(Kviz).filter_by(nazev='Existing Quiz Name').count()
        assert count == 1


def test_import_csv_wrong_file_type(client, app):
    """Test CSV import with non-CSV file returns error."""
    data = {
        'quiz_name': 'Wrong Type Quiz',
        'quiz_description': 'Wrong file type',
        'time_limit': 15,
        'csv_file': (io.BytesIO(b'Not a CSV'), 'test.txt')
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    
    with app.app_context():
        # Verify no quiz was created
        quiz = Kviz.query.filter_by(nazev='Wrong Type Quiz').first()
        assert quiz is None


def test_import_csv_preserves_order(client, app):
    """Test that CSV import preserves question order."""
    csv_content = """otazka,spravna_odpoved,spatna_odpoved1,spatna_odpoved2,spatna_odpoved3
First question?,1,2,3,4
Second question?,2,3,4,5
Third question?,3,4,5,6"""
    
    data = {
        'quiz_name': 'Ordered Quiz',
        'quiz_description': 'Order matters',
        'time_limit': 15,
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'ordered.csv')
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    
    with app.app_context():
        quiz = Kviz.query.filter_by(nazev='Ordered Quiz').first()
        questions = db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz.kviz_id).order_by(KvizOtazky.poradi).all()
        
        assert len(questions) == 3
        assert questions[0].poradi == 1
        assert questions[1].poradi == 2
        assert questions[2].poradi == 3
        
        # Verify actual question content order
        q1 = Otazka.query.get(questions[0].otazka_id_fk)
        q2 = Otazka.query.get(questions[1].otazka_id_fk)
        q3 = Otazka.query.get(questions[2].otazka_id_fk)
        
        assert q1.otazka == 'First question?'
        assert q2.otazka == 'Second question?'
        assert q3.otazka == 'Third question?'


def test_import_csv_skips_invalid_rows(client, app):
    """Test that CSV import skips rows with missing data."""
    csv_content = """otazka,spravna_odpoved,spatna_odpoved1,spatna_odpoved2,spatna_odpoved3
Valid question?,Answer,Wrong1,Wrong2,Wrong3
Invalid question?,,Wrong1,Wrong2,Wrong3
Another valid?,Answer2,Wrong1,Wrong2,Wrong3"""
    
    data = {
        'quiz_name': 'Partial Quiz',
        'quiz_description': 'Some invalid rows',
        'time_limit': 15,
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'partial.csv')
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    
    with app.app_context():
        quiz = Kviz.query.filter_by(nazev='Partial Quiz').first()
        assert quiz is not None
        
        # Only 2 valid questions should be imported (row 2 is invalid)
        questions = db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz.kviz_id).count()
        assert questions == 2


def test_import_csv_duplicate_questions_in_csv(client, app):
    """Test that CSV import skips duplicate questions within the same CSV file."""
    csv_content = """otazka,spravna_odpoved,spatna_odpoved1,spatna_odpoved2,spatna_odpoved3
What is 2+2?,4,3,5,6
What is 3+3?,6,5,7,8
What is 2+2?,4,3,5,6
What is 4+4?,8,7,9,10
What is 3+3?,6,5,7,8"""
    
    data = {
        'quiz_name': 'Duplicate Quiz',
        'quiz_description': 'Has duplicate questions in CSV',
        'time_limit': 15,
        'csv_file': (io.BytesIO(csv_content.encode('utf-8')), 'duplicates.csv')
    }
    
    response = client.post('/admin/kviz/import', data=data, follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        quiz = Kviz.query.filter_by(nazev='Duplicate Quiz').first()
        assert quiz is not None
        
        # Only 3 unique questions should be imported (2+2, 3+3, 4+4)
        # even though the CSV has 5 rows
        questions = db.session.query(KvizOtazky).filter_by(kviz_id_fk=quiz.kviz_id).order_by(KvizOtazky.poradi).all()
        assert len(questions) == 3
        
        # Verify the questions are the unique ones
        q1 = Otazka.query.get(questions[0].otazka_id_fk)
        q2 = Otazka.query.get(questions[1].otazka_id_fk)
        q3 = Otazka.query.get(questions[2].otazka_id_fk)
        
        assert q1.otazka == 'What is 2+2?'
        assert q2.otazka == 'What is 3+3?'
        assert q3.otazka == 'What is 4+4?'
        
        # Verify order is correct (poradi)
        assert questions[0].poradi == 1
        assert questions[1].poradi == 2
        assert questions[2].poradi == 3
