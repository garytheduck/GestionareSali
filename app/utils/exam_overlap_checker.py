"""
Utilitar pentru verificarea suprapunerilor la programarea examenelor
"""
from datetime import datetime, timedelta
from app.models.exam import Exam
from app.models.course import Course
from sqlalchemy import and_, or_
import logging

logger = logging.getLogger(__name__)

def check_room_overlap(room_id, start_time, end_time, exclude_exam_id=None):
    """
    Verifică dacă există suprapuneri pentru o sală într-un interval orar dat
    
    Args:
        room_id (int): ID-ul sălii
        start_time (datetime): Ora de început
        end_time (datetime): Ora de sfârșit
        exclude_exam_id (int, optional): ID-ul examenului de exclus din verificare (pentru actualizări)
        
    Returns:
        bool: True dacă există suprapuneri, False în caz contrar
    """
    query = Exam.query.filter(
        Exam.room_id == room_id,
        Exam.is_active == True,
        or_(
            # Intervalul nou începe în timpul unui examen existent
            and_(start_time >= Exam.start_time, start_time < Exam.end_time),
            # Intervalul nou se termină în timpul unui examen existent
            and_(end_time > Exam.start_time, end_time <= Exam.end_time),
            # Intervalul nou acoperă complet un examen existent
            and_(start_time <= Exam.start_time, end_time >= Exam.end_time)
        )
    )
    
    # Excludem examenul curent din verificare (pentru actualizări)
    if exclude_exam_id:
        query = query.filter(Exam.id != exclude_exam_id)
    
    return query.count() > 0

def check_teacher_overlap(teacher_id, start_time, end_time, exclude_exam_id=None):
    """
    Verifică dacă există suprapuneri pentru un profesor într-un interval orar dat
    
    Args:
        teacher_id (int): ID-ul profesorului
        start_time (datetime): Ora de început
        end_time (datetime): Ora de sfârșit
        exclude_exam_id (int, optional): ID-ul examenului de exclus din verificare (pentru actualizări)
        
    Returns:
        bool: True dacă există suprapuneri, False în caz contrar
    """
    # Găsim toate examenele active pentru cursurile predate de acest profesor
    courses_with_exams = Course.query.filter(
        Course.teacher_id == teacher_id,
        Course.is_active == True
    ).with_entities(Course.id).all()
    
    course_ids = [course.id for course in courses_with_exams]
    
    if not course_ids:
        return False
    
    query = Exam.query.filter(
        Exam.course_id.in_(course_ids),
        Exam.is_active == True,
        or_(
            # Intervalul nou începe în timpul unui examen existent
            and_(start_time >= Exam.start_time, start_time < Exam.end_time),
            # Intervalul nou se termină în timpul unui examen existent
            and_(end_time > Exam.start_time, end_time <= Exam.end_time),
            # Intervalul nou acoperă complet un examen existent
            and_(start_time <= Exam.start_time, end_time >= Exam.end_time)
        )
    )
    
    # Excludem examenul curent din verificare (pentru actualizări)
    if exclude_exam_id:
        query = query.filter(Exam.id != exclude_exam_id)
    
    return query.count() > 0

def check_assistant_overlap(assistant_id, start_time, end_time, exclude_exam_id=None):
    """
    Verifică dacă există suprapuneri pentru un asistent într-un interval orar dat
    
    Args:
        assistant_id (int): ID-ul asistentului
        start_time (datetime): Ora de început
        end_time (datetime): Ora de sfârșit
        exclude_exam_id (int, optional): ID-ul examenului de exclus din verificare (pentru actualizări)
        
    Returns:
        bool: True dacă există suprapuneri, False în caz contrar
    """
    # Găsim toate examenele active pentru cursurile asistate de acest asistent
    courses_with_exams = Course.query.filter(
        Course.assistant_id == assistant_id,
        Course.is_active == True
    ).with_entities(Course.id).all()
    
    course_ids = [course.id for course in courses_with_exams]
    
    if not course_ids:
        return False
    
    query = Exam.query.filter(
        Exam.course_id.in_(course_ids),
        Exam.is_active == True,
        or_(
            # Intervalul nou începe în timpul unui examen existent
            and_(start_time >= Exam.start_time, start_time < Exam.end_time),
            # Intervalul nou se termină în timpul unui examen existent
            and_(end_time > Exam.start_time, end_time <= Exam.end_time),
            # Intervalul nou acoperă complet un examen existent
            and_(start_time <= Exam.start_time, end_time >= Exam.end_time)
        )
    )
    
    # Excludem examenul curent din verificare (pentru actualizări)
    if exclude_exam_id:
        query = query.filter(Exam.id != exclude_exam_id)
    
    return query.count() > 0

def check_student_group_overlap(group_name, faculty, study_program, year_of_study, start_time, end_time, exclude_exam_id=None):
    """
    Verifică dacă există suprapuneri pentru un grup de studenți într-un interval orar dat
    
    Args:
        group_name (str): Numele grupei
        faculty (str): Facultatea
        study_program (str): Programul de studiu
        year_of_study (int): Anul de studiu
        start_time (datetime): Ora de început
        end_time (datetime): Ora de sfârșit
        exclude_exam_id (int, optional): ID-ul examenului de exclus din verificare (pentru actualizări)
        
    Returns:
        bool: True dacă există suprapuneri, False în caz contrar
    """
    # Găsim toate cursurile pentru această grupă
    courses = Course.query.filter(
        Course.group_name == group_name,
        Course.faculty == faculty,
        Course.study_program == study_program,
        Course.year_of_study == year_of_study,
        Course.is_active == True
    ).with_entities(Course.id).all()
    
    course_ids = [course.id for course in courses]
    
    if not course_ids:
        return False
    
    query = Exam.query.filter(
        Exam.course_id.in_(course_ids),
        Exam.is_active == True,
        or_(
            # Intervalul nou începe în timpul unui examen existent
            and_(start_time >= Exam.start_time, start_time < Exam.end_time),
            # Intervalul nou se termină în timpul unui examen existent
            and_(end_time > Exam.start_time, end_time <= Exam.end_time),
            # Intervalul nou acoperă complet un examen existent
            and_(start_time <= Exam.start_time, end_time >= Exam.end_time)
        )
    )
    
    # Excludem examenul curent din verificare (pentru actualizări)
    if exclude_exam_id:
        query = query.filter(Exam.id != exclude_exam_id)
    
    return query.count() > 0

def get_overlapping_exams(exam_data, exclude_exam_id=None):
    """
    Obține toate examenele care se suprapun cu datele furnizate
    
    Args:
        exam_data (dict): Datele examenului (room_id, start_time, end_time, course_id)
        exclude_exam_id (int, optional): ID-ul examenului de exclus din verificare (pentru actualizări)
        
    Returns:
        dict: Dicționar cu suprapunerile găsite, grupate pe categorii
    """
    room_id = exam_data.get('room_id')
    start_time = exam_data.get('start_time')
    end_time = exam_data.get('end_time')
    course_id = exam_data.get('course_id')
    
    # Obținem informații despre curs
    course = Course.query.get(course_id)
    if not course:
        return {'error': 'Cursul nu a fost găsit'}
    
    overlaps = {
        'room': [],
        'teacher': [],
        'assistant': [],
        'student_group': []
    }
    
    # Verificăm suprapunerile pentru sală
    room_query = Exam.query.filter(
        Exam.room_id == room_id,
        Exam.is_active == True,
        or_(
            and_(start_time >= Exam.start_time, start_time < Exam.end_time),
            and_(end_time > Exam.start_time, end_time <= Exam.end_time),
            and_(start_time <= Exam.start_time, end_time >= Exam.end_time)
        )
    )
    
    if exclude_exam_id:
        room_query = room_query.filter(Exam.id != exclude_exam_id)
    
    room_overlaps = room_query.all()
    for exam in room_overlaps:
        overlaps['room'].append({
            'exam_id': exam.id,
            'course_name': exam.course.name,
            'start_time': exam.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': exam.end_time.strftime('%Y-%m-%d %H:%M')
        })
    
    # Verificăm suprapunerile pentru profesor
    if course.teacher_id:
        teacher_courses = Course.query.filter(
            Course.teacher_id == course.teacher_id,
            Course.is_active == True
        ).with_entities(Course.id).all()
        
        teacher_course_ids = [c.id for c in teacher_courses]
        
        teacher_query = Exam.query.filter(
            Exam.course_id.in_(teacher_course_ids),
            Exam.is_active == True,
            or_(
                and_(start_time >= Exam.start_time, start_time < Exam.end_time),
                and_(end_time > Exam.start_time, end_time <= Exam.end_time),
                and_(start_time <= Exam.start_time, end_time >= Exam.end_time)
            )
        )
        
        if exclude_exam_id:
            teacher_query = teacher_query.filter(Exam.id != exclude_exam_id)
        
        teacher_overlaps = teacher_query.all()
        for exam in teacher_overlaps:
            overlaps['teacher'].append({
                'exam_id': exam.id,
                'course_name': exam.course.name,
                'start_time': exam.start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': exam.end_time.strftime('%Y-%m-%d %H:%M')
            })
    
    # Verificăm suprapunerile pentru asistent
    if course.assistant_id:
        assistant_courses = Course.query.filter(
            Course.assistant_id == course.assistant_id,
            Course.is_active == True
        ).with_entities(Course.id).all()
        
        assistant_course_ids = [c.id for c in assistant_courses]
        
        assistant_query = Exam.query.filter(
            Exam.course_id.in_(assistant_course_ids),
            Exam.is_active == True,
            or_(
                and_(start_time >= Exam.start_time, start_time < Exam.end_time),
                and_(end_time > Exam.start_time, end_time <= Exam.end_time),
                and_(start_time <= Exam.start_time, end_time >= Exam.end_time)
            )
        )
        
        if exclude_exam_id:
            assistant_query = assistant_query.filter(Exam.id != exclude_exam_id)
        
        assistant_overlaps = assistant_query.all()
        for exam in assistant_overlaps:
            overlaps['assistant'].append({
                'exam_id': exam.id,
                'course_name': exam.course.name,
                'start_time': exam.start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': exam.end_time.strftime('%Y-%m-%d %H:%M')
            })
    
    # Verificăm suprapunerile pentru grupa de studenți
    group_courses = Course.query.filter(
        Course.group_name == course.group_name,
        Course.faculty == course.faculty,
        Course.study_program == course.study_program,
        Course.year_of_study == course.year_of_study,
        Course.is_active == True
    ).with_entities(Course.id).all()
    
    group_course_ids = [c.id for c in group_courses]
    
    group_query = Exam.query.filter(
        Exam.course_id.in_(group_course_ids),
        Exam.is_active == True,
        or_(
            and_(start_time >= Exam.start_time, start_time < Exam.end_time),
            and_(end_time > Exam.start_time, end_time <= Exam.end_time),
            and_(start_time <= Exam.start_time, end_time >= Exam.end_time)
        )
    )
    
    if exclude_exam_id:
        group_query = group_query.filter(Exam.id != exclude_exam_id)
    
    group_overlaps = group_query.all()
    for exam in group_overlaps:
        overlaps['student_group'].append({
            'exam_id': exam.id,
            'course_name': exam.course.name,
            'start_time': exam.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': exam.end_time.strftime('%Y-%m-%d %H:%M')
        })
    
    return overlaps
