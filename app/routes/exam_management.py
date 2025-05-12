"""
API endpoints pentru managementul examenelor
"""
from flask import Blueprint, request, jsonify, current_app, send_file
from app import db
from app.models.exam import Exam, ExamRegistration
from app.models import Room
from app.models.course import Course, ExamType
from app.models import User
from werkzeug.exceptions import BadRequest, NotFound
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
from app.utils.exam_overlap_checker import check_room_overlap, check_teacher_overlap, check_assistant_overlap, check_student_group_overlap, get_overlapping_exams
# Temporar comentat pentru a evita eroarea
# from app.utils.exam_report_generator import generate_exam_schedule_excel, generate_exam_schedule_pdf, generate_exam_completion_stats
# Definim funcții placeholder
def generate_exam_schedule_excel(*args, **kwargs):
    return None

def generate_exam_schedule_pdf(*args, **kwargs):
    return None

def generate_exam_completion_stats(*args, **kwargs):
    return {}
from app.utils.email_service import send_exam_proposal_notification, send_exam_approval_notification, send_exam_rejection_notification
import io
import logging

logger = logging.getLogger(__name__)

# Creăm un Blueprint pentru managementul examenelor
exam_bp = Blueprint('exam', __name__, url_prefix='/api/exams')

@exam_bp.route('/', methods=['GET'])
@jwt_required()
def get_exams():
    """
    Obține lista examenelor cu opțiuni de filtrare
    
    Query params:
        course_id (int): Filtrare după ID-ul cursului
        room_id (int): Filtrare după ID-ul sălii
        start_date (str): Filtrare după data de început (format: YYYY-MM-DD)
        end_date (str): Filtrare după data de sfârșit (format: YYYY-MM-DD)
        exam_type (str): Filtrare după tipul de examen
        semester (str): Filtrare după semestru
        academic_year (str): Filtrare după anul academic
    """
    try:
        # Preluăm parametrii din query string
        course_id = request.args.get('course_id')
        room_id = request.args.get('room_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        exam_type = request.args.get('exam_type')
        semester = request.args.get('semester')
        academic_year = request.args.get('academic_year')
        
        # Construim query-ul
        query = Exam.query
        
        if course_id:
            query = query.filter(Exam.course_id == int(course_id))
        if room_id:
            query = query.filter(Exam.room_id == int(room_id))
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Exam.start_time >= start_date_obj)
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            # Adăugăm 23:59:59 pentru a include toată ziua
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
            query = query.filter(Exam.end_time <= end_date_obj)
        if exam_type:
            query = query.filter(Exam.exam_type == exam_type)
        if semester:
            query = query.filter(Exam.semester == semester)
        if academic_year:
            query = query.filter(Exam.academic_year == academic_year)
        
        # Includem doar examenele active
        query = query.filter(Exam.is_active == True)
        
        # Executăm query-ul
        exams = query.all()
        
        # Serializăm rezultatele
        result = []
        for exam in exams:
            result.append({
                'id': exam.id,
                'course': {
                    'id': exam.course.id,
                    'name': exam.course.name,
                    'code': exam.course.code,
                    'study_program': exam.course.study_program,
                    'year_of_study': exam.course.year_of_study
                },
                'room': {
                    'id': exam.room.id,
                    'name': exam.room.name,
                    'building': exam.room.building,
                    'capacity': exam.room.capacity
                },
                'start_time': exam.start_time.isoformat(),
                'end_time': exam.end_time.isoformat(),
                'exam_type': exam.exam_type,
                'semester': exam.semester,
                'academic_year': exam.academic_year,
                'max_students': exam.max_students,
                'notes': exam.notes,
                'registrations_count': len(exam.registrations)
            })
        
        return jsonify({
            'status': 'success',
            'data': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting exams: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve exams',
            'error': str(e)
        }), 500


@exam_bp.route('/', methods=['POST'])
@jwt_required()
def create_exam():
    """
    Creează un nou examen
    
    Body params:
        course_id (int): ID-ul cursului
        room_id (int): ID-ul sălii
        start_time (str): Data și ora de început (format: YYYY-MM-DDTHH:MM:SS)
        end_time (str): Data și ora de sfârșit (format: YYYY-MM-DDTHH:MM:SS)
        exam_type (str): Tipul de examen
        semester (str): Semestrul
        academic_year (str): Anul academic
        max_students (int, optional): Capacitatea maximă de studenți
        notes (str, optional): Note sau observații
    """
    try:
        # Preluăm datele din corpul cererii
        data = request.get_json()
        
        # Verificăm câmpurile obligatorii
        required_fields = ['course_id', 'room_id', 'start_time', 'end_time', 'exam_type', 'semester', 'academic_year']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Verificăm dacă cursul există
        course = Course.query.get(data['course_id'])
        if not course:
            return jsonify({
                'status': 'error',
                'message': f'Course with ID {data["course_id"]} not found'
            }), 404
        
        # Verificăm dacă sala există
        room = Room.query.get(data['room_id'])
        if not room:
            return jsonify({
                'status': 'error',
                'message': f'Room with ID {data["room_id"]} not found'
            }), 404
        
        # Convertim datele de timp
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        
        # Verificăm dacă data de început este înainte de data de sfârșit
        if start_time >= end_time:
            return jsonify({
                'status': 'error',
                'message': 'Start time must be before end time'
            }), 400
        
        # Verificăm suprapunerile pentru sală, profesor, asistent și grupă de studenți
        course = Course.query.get(course_id)
        if not course:
            return jsonify({
                'status': 'error',
                'message': f'Course with ID {course_id} not found'
            }), 404
            
        # Verificăm suprapunerile pentru sală
        if check_room_overlap(room_id, start_time, end_time):
            return jsonify({
                'status': 'error',
                'message': 'Room is not available during the specified time interval',
                'overlap_type': 'room'
            }), 409  # Conflict
            
        # Verificăm suprapunerile pentru profesor
        if course.teacher_id and check_teacher_overlap(course.teacher_id, start_time, end_time):
            return jsonify({
                'status': 'error',
                'message': 'Teacher has another exam scheduled during the specified time interval',
                'overlap_type': 'teacher'
            }), 409  # Conflict
            
        # Verificăm suprapunerile pentru asistent
        if course.assistant_id and check_assistant_overlap(course.assistant_id, start_time, end_time):
            return jsonify({
                'status': 'error',
                'message': 'Assistant has another exam scheduled during the specified time interval',
                'overlap_type': 'assistant'
            }), 409  # Conflict
            
        # Verificăm suprapunerile pentru grupa de studenți
        if check_student_group_overlap(course.group_name, course.faculty, course.study_program, course.year_of_study, start_time, end_time):
            return jsonify({
                'status': 'error',
                'message': 'Student group has another exam scheduled during the specified time interval',
                'overlap_type': 'student_group'
            }), 409  # Conflict
            
        # Alternativ, putem obține toate suprapunerile într-un singur apel
        exam_data = {
            'room_id': room_id,
            'start_time': start_time,
            'end_time': end_time,
            'course_id': course_id
        }
        
        overlaps = get_overlapping_exams(exam_data)
        
        # Dacă există suprapuneri, le returnam pentru a fi afișate în frontend
        has_overlaps = any(len(overlaps[key]) > 0 for key in overlaps if key != 'error')
        
        if has_overlaps:
            return jsonify({
                'status': 'error',
                'message': 'There are scheduling conflicts for this exam',
                'overlaps': overlaps
            }), 409  # Conflict
        
        # Creăm examenul
        exam = Exam(
            course_id=data['course_id'],
            room_id=data['room_id'],
            start_time=start_time,
            end_time=end_time,
            exam_type=data['exam_type'],
            semester=data['semester'],
            academic_year=data['academic_year'],
            max_students=data.get('max_students'),
            notes=data.get('notes')
        )
        
        # Salvăm în baza de date
        db.session.add(exam)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Exam created successfully',
            'data': {
                'id': exam.id,
                'course': {
                    'id': exam.course.id,
                    'name': exam.course.name
                },
                'room': {
                    'id': exam.room.id,
                    'name': exam.room.name
                },
                'start_time': exam.start_time.isoformat(),
                'end_time': exam.end_time.isoformat(),
                'exam_type': exam.exam_type,
                'semester': exam.semester,
                'academic_year': exam.academic_year,
                'max_students': exam.max_students,
                'notes': exam.notes
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating exam: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to create exam',
            'error': str(e)
        }), 500


@exam_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_exam(id):
    """
    Obține detaliile unui examen specific
    
    Path params:
        id (int): ID-ul examenului
    """
    try:
        exam = Exam.query.get(id)
        
        if not exam or not exam.is_active:
            return jsonify({
                'status': 'error',
                'message': f'Exam with ID {id} not found'
            }), 404
        
        # Calculăm numărul de înregistrări
        registrations_count = len(exam.registrations)
        
        # Serializăm rezultatul
        result = {
            'id': exam.id,
            'course': {
                'id': exam.course.id,
                'name': exam.course.name,
                'code': exam.course.code,
                'study_program': exam.course.study_program,
                'year_of_study': exam.course.year_of_study
            },
            'room': {
                'id': exam.room.id,
                'name': exam.room.name,
                'building': exam.room.building,
                'capacity': exam.room.capacity
            },
            'start_time': exam.start_time.isoformat(),
            'end_time': exam.end_time.isoformat(),
            'exam_type': exam.exam_type,
            'semester': exam.semester,
            'academic_year': exam.academic_year,
            'max_students': exam.max_students,
            'notes': exam.notes,
            'registrations_count': registrations_count,
            'created_at': exam.created_at.isoformat() if exam.created_at else None,
            'updated_at': exam.updated_at.isoformat() if exam.updated_at else None
        }
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting exam {id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve exam with ID {id}',
            'error': str(e)
        }), 500


@exam_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_exam(id):
    """
    Actualizează un examen existent
    
    Path params:
        id (int): ID-ul examenului
        
    Body params:
        room_id (int, optional): ID-ul sălii
        start_time (str, optional): Data și ora de început (format: YYYY-MM-DDTHH:MM:SS)
        end_time (str, optional): Data și ora de sfârșit (format: YYYY-MM-DDTHH:MM:SS)
        exam_type (str, optional): Tipul de examen
        max_students (int, optional): Capacitatea maximă de studenți
        notes (str, optional): Note sau observații
    """
    try:
        # Preluăm datele din corpul cererii
        data = request.get_json()
        
        # Verificăm dacă examenul există
        exam = Exam.query.get(id)
        
        if not exam or not exam.is_active:
            return jsonify({
                'status': 'error',
                'message': f'Exam with ID {id} not found'
            }), 404
        
        # Nu permitem schimbarea cursului sau a semestrului/anului academic după creare
        if 'course_id' in data:
            return jsonify({
                'status': 'error',
                'message': 'Changing the course for an existing exam is not allowed'
            }), 400
            
        if 'semester' in data or 'academic_year' in data:
            return jsonify({
                'status': 'error',
                'message': 'Changing the semester or academic year for an existing exam is not allowed'
            }), 400
        
        # Procesăm actualizarea sălii dacă este specificată
        if 'room_id' in data:
            room = Room.query.get(data['room_id'])
            if not room:
                return jsonify({
                    'status': 'error',
                    'message': f'Room with ID {data["room_id"]} not found'
                }), 404
            exam.room_id = data['room_id']
        
        # Procesăm actualizarea datelor de timp
        start_time = exam.start_time
        end_time = exam.end_time
        
        if 'start_time' in data:
            start_time = datetime.fromisoformat(data['start_time'])
        
        if 'end_time' in data:
            end_time = datetime.fromisoformat(data['end_time'])
        
        # Verificăm dacă data de început este înainte de data de sfârșit
        if start_time >= end_time:
            return jsonify({
                'status': 'error',
                'message': 'Start time must be before end time'
            }), 400
        
        # Verificăm suprapunerile pentru sală, profesor, asistent și grupă de studenți
        room_id = data.get('room_id') or exam.room_id
        
        # Verificăm suprapunerile pentru sală
        if check_room_overlap(room_id, start_time, end_time, exclude_exam_id=id):
            return jsonify({
                'status': 'error',
                'message': 'Room is not available during the specified time interval',
                'overlap_type': 'room'
            }), 409  # Conflict
            
        # Verificăm suprapunerile pentru profesor
        if exam.course.teacher_id and check_teacher_overlap(exam.course.teacher_id, start_time, end_time, exclude_exam_id=id):
            return jsonify({
                'status': 'error',
                'message': 'Teacher has another exam scheduled during the specified time interval',
                'overlap_type': 'teacher'
            }), 409  # Conflict
            
        # Verificăm suprapunerile pentru asistent
        if exam.course.assistant_id and check_assistant_overlap(exam.course.assistant_id, start_time, end_time, exclude_exam_id=id):
            return jsonify({
                'status': 'error',
                'message': 'Assistant has another exam scheduled during the specified time interval',
                'overlap_type': 'assistant'
            }), 409  # Conflict
            
        # Verificăm suprapunerile pentru grupa de studenți
        if check_student_group_overlap(
            exam.course.group_name, 
            exam.course.faculty, 
            exam.course.study_program, 
            exam.course.year_of_study, 
            start_time, 
            end_time, 
            exclude_exam_id=id
        ):
            return jsonify({
                'status': 'error',
                'message': 'Student group has another exam scheduled during the specified time interval',
                'overlap_type': 'student_group'
            }), 409  # Conflict
            
        # Alternativ, putem obține toate suprapunerile într-un singur apel
        exam_data = {
            'room_id': room_id,
            'start_time': start_time,
            'end_time': end_time,
            'course_id': exam.course_id
        }
        
        overlaps = get_overlapping_exams(exam_data, exclude_exam_id=id)
        
        # Dacă există suprapuneri, le returnam pentru a fi afișate în frontend
        has_overlaps = any(len(overlaps[key]) > 0 for key in overlaps if key != 'error')
        
        if has_overlaps:
            return jsonify({
                'status': 'error',
                'message': 'There are scheduling conflicts for this exam',
                'overlaps': overlaps
            }), 409  # Conflict
        
        # Actualizăm examenul
        if 'start_time' in data:
            exam.start_time = start_time
        
        if 'end_time' in data:
            exam.end_time = end_time
        
        if 'exam_type' in data:
            exam.exam_type = data['exam_type']
        
        if 'max_students' in data:
            exam.max_students = data.get('max_students')
        
        if 'notes' in data:
            exam.notes = data.get('notes')
        
        # Actualizăm timestamp-ul
        exam.updated_at = datetime.utcnow()
        
        # Salvăm în baza de date
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Exam updated successfully',
            'data': {
                'id': exam.id,
                'course': {
                    'id': exam.course.id,
                    'name': exam.course.name
                },
                'room': {
                    'id': exam.room.id,
                    'name': exam.room.name
                },
                'start_time': exam.start_time.isoformat(),
                'end_time': exam.end_time.isoformat(),
                'exam_type': exam.exam_type,
                'semester': exam.semester,
                'academic_year': exam.academic_year,
                'max_students': exam.max_students,
                'notes': exam.notes
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating exam {id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to update exam with ID {id}',
            'error': str(e)
        }), 500


@exam_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_exam(id):
    """
    Șterge (dezactivează) un examen
    
    Path params:
        id (int): ID-ul examenului
    """
    try:
        exam = Exam.query.get(id)
        
        if not exam or not exam.is_active:
            return jsonify({
                'status': 'error',
                'message': f'Exam with ID {id} not found'
            }), 404
        
        # Nu ștergem complet, doar dezactivăm
        exam.is_active = False
        exam.updated_at = datetime.utcnow()
        
        # Salvăm modificările în baza de date
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Exam with ID {id} deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting exam {id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete exam with ID {id}',
            'error': str(e)
        }), 500


@exam_bp.route('/export/excel', methods=['GET'])
@jwt_required()
def export_exam_schedule_excel():
    """
    Exportă programarea examenelor în format Excel
    
    Query params:
        faculty (str): Filtrare după facultate
        study_program (str): Filtrare după program de studiu
        year_of_study (int): Filtrare după an de studiu
        group_name (str): Filtrare după grupă
        exam_type (str): Filtrare după tip examen
    """
    try:
        # Preluăm parametrii de filtrare
        filters = {
            'faculty': request.args.get('faculty'),
            'study_program': request.args.get('study_program'),
            'year_of_study': request.args.get('year_of_study'),
            'group_name': request.args.get('group_name'),
            'exam_type': request.args.get('exam_type')
        }
        
        # Generăm raportul Excel
        excel_data = generate_exam_schedule_excel(filters)
        
        # Pregătim fișierul pentru download
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"programare_examene_{timestamp}.xlsx"
        
        return send_file(
            io.BytesIO(excel_data),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error generating Excel report: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate Excel report',
            'error': str(e)
        }), 500


@exam_bp.route('/export/pdf', methods=['GET'])
@jwt_required()
def export_exam_schedule_pdf():
    """
    Exportă programarea examenelor în format PDF
    
    Query params:
        faculty (str): Filtrare după facultate
        study_program (str): Filtrare după program de studiu
        year_of_study (int): Filtrare după an de studiu
        group_name (str): Filtrare după grupă
        exam_type (str): Filtrare după tip examen
    """
    try:
        # Preluăm parametrii de filtrare
        filters = {
            'faculty': request.args.get('faculty'),
            'study_program': request.args.get('study_program'),
            'year_of_study': request.args.get('year_of_study'),
            'group_name': request.args.get('group_name'),
            'exam_type': request.args.get('exam_type')
        }
        
        # Generăm raportul PDF
        pdf_data = generate_exam_schedule_pdf(filters)
        
        # Pregătim fișierul pentru download
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"programare_examene_{timestamp}.pdf"
        
        return send_file(
            io.BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF report: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate PDF report',
            'error': str(e)
        }), 500


@exam_bp.route('/stats/completion', methods=['GET'])
@jwt_required()
def get_exam_completion_stats():
    """
    Obține statistici despre gradul de completare a programării examenelor
    """
    try:
        # Generăm statisticile
        stats = generate_exam_completion_stats()
        
        return jsonify({
            'status': 'success',
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating exam completion stats: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate exam completion statistics',
            'error': str(e)
        }), 500
