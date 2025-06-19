"""
Script pentru adăugarea unei discipline de test cu profesorul teacher.test@usm.ro
"""
from app import create_app, db
from app.models.user import User
from app.models.course import Course, ExamType
import random
import string

def generate_random_code(length=6):
    """Generează un cod aleatoriu pentru disciplină"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def add_test_course():
    """Adaugă o disciplină de test cu profesorul teacher.test@usm.ro"""
    # Creăm aplicația Flask
    app = create_app()
    
    with app.app_context():
        # Verificăm dacă profesorul de test există
        test_teacher = User.query.filter_by(email='teacher.test@usm.ro').first()
        
        if not test_teacher:
            print("Profesorul de test nu există în baza de date. Adăugați-l mai întâi.")
            return
        
        # Verificăm dacă există deja o disciplină pentru acest profesor
        existing_course = Course.query.filter_by(teacher_id=test_teacher.id).first()
        
        if existing_course:
            print(f"Există deja o disciplină pentru profesorul de test: {existing_course.name} (ID: {existing_course.id})")
            return
        
        # Generăm un cod unic pentru disciplină
        code = f"TEST{generate_random_code()}"
        
        # Creăm o disciplină nouă
        new_course = Course(
            code=code,
            name="Disciplină de Test",
            faculty="Facultatea de Inginerie Electrică și Știința Calculatoarelor",
            department="Calculatoare",
            study_program="Calculatoare",
            year_of_study=3,
            semester="2",
            credits=5,
            group_name="3201A",  # Grupa pentru care adăugăm disciplina
            exam_type=ExamType.EXAM,
            teacher_id=test_teacher.id
        )
        
        # Adăugăm disciplina în baza de date
        db.session.add(new_course)
        db.session.commit()
        
        print(f"Disciplina de test a fost adăugată cu succes: {new_course.name} (ID: {new_course.id})")

if __name__ == "__main__":
    add_test_course()
