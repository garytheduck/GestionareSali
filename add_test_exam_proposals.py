"""
Script pentru adăugarea propunerilor de examene pentru profesorul de test
"""
from app import create_app, db
from app.models.user import User
from app.models.course import Course
from datetime import datetime, timedelta
import random

def add_test_exam_proposals():
    """Adaugă propuneri de examene pentru profesorul de test"""
    # Creăm aplicația Flask
    app = create_app()
    
    with app.app_context():
        # Găsim profesorul de test
        test_teacher = User.query.filter_by(email='teacher.test@usm.ro').first()
        
        if not test_teacher:
            print("Profesorul de test nu există în baza de date. Adăugați-l mai întâi.")
            return
        
        # Găsim disciplina asociată profesorului de test
        test_course = Course.query.filter_by(teacher_id=test_teacher.id).first()
        
        if not test_course:
            print("Nu există o disciplină asociată profesorului de test. Adăugați mai întâi o disciplină.")
            return
        
        print(f"Am găsit disciplina: {test_course.name} (ID: {test_course.id})")
        
        # Creăm 5 propuneri de examene pentru disciplina găsită
        # Vom folosi date diferite pentru fiecare propunere
        
        # Data de bază pentru propuneri (începând de mâine)
        base_date = datetime.now() + timedelta(days=1)
        
        # Creăm propunerile
        for i in range(5):
            # Generăm o dată aleatoare în următoarele 30 de zile
            random_days = random.randint(1, 30)
            proposed_date = base_date + timedelta(days=random_days)
            
            # Generăm o oră aleatoare între 8:00 și 18:00
            random_hour = random.randint(8, 18)
            proposed_date = proposed_date.replace(hour=random_hour, minute=0, second=0, microsecond=0)
            
            # Actualizăm disciplina cu data propusă
            # Vom crea copii ale disciplinei pentru a avea mai multe propuneri
            new_course = Course(
                code=f"{test_course.code}-{i+1}",
                name=f"{test_course.name} - Propunere {i+1}",
                faculty=test_course.faculty,
                department=test_course.department,
                study_program=test_course.study_program,
                year_of_study=test_course.year_of_study,
                semester=test_course.semester,
                credits=test_course.credits,
                group_name=test_course.group_name,
                exam_type=test_course.exam_type,
                teacher_id=test_teacher.id,
                proposed_date=proposed_date,
                status='pending'
            )
            
            db.session.add(new_course)
            print(f"Adăugat propunere {i+1}: {new_course.name} pentru data {proposed_date}")
        
        # Salvăm modificările în baza de date
        db.session.commit()
        
        print("Propunerile de examene au fost adăugate cu succes!")

if __name__ == "__main__":
    add_test_exam_proposals()
