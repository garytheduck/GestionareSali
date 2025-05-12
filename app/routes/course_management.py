"""
API endpoints pentru managementul disciplinelor
"""
from flask import Blueprint, request, jsonify, current_app, send_file
from app import db
from app.models import Course, ExamType, User
from app.models.group_leader import GroupLeader
from app.utils.orar_client import OrarClient
from werkzeug.exceptions import BadRequest, NotFound
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from app.utils.email_service import send_exam_proposal_notification, send_exam_approval_notification, send_exam_rejection_notification
from app.utils.exam_overlap_checker import check_room_overlap, check_teacher_overlap, check_assistant_overlap, check_student_group_overlap
import io
import logging

logger = logging.getLogger(__name__)

# Creăm un Blueprint pentru managementul disciplinelor
course_bp = Blueprint('course', __name__, url_prefix='/api/courses')

# Inițializăm clientul pentru sistemul Orar
orar_client = OrarClient()

def get_courses_data(filters=None):
    """
    Funcție utilitară pentru a obține datele cursurilor cu filtre opționale.
    Poate fi importată și folosită de alte module.
    
    Args:
        filters (dict): Filtre opționale (faculty, department, etc.)
        
    Returns:
        list: Lista de cursuri serializate
    """
    try:
        # Construim query-ul
        query = Course.query
        
        if filters:
            if 'faculty' in filters and filters['faculty']:
                query = query.filter(Course.faculty == filters['faculty'])
            if 'department' in filters and filters['department']:
                query = query.filter(Course.department == filters['department'])
            if 'study_program' in filters and filters['study_program']:
                query = query.filter(Course.study_program == filters['study_program'])
            if 'year_of_study' in filters and filters['year_of_study']:
                query = query.filter(Course.year_of_study == int(filters['year_of_study']))
            if 'semester' in filters and filters['semester']:
                query = query.filter(Course.semester == filters['semester'])
            if 'group_name' in filters and filters['group_name']:
                query = query.filter(Course.group_name == filters['group_name'])
            if 'exam_type' in filters and filters['exam_type']:
                query = query.filter(Course.exam_type == ExamType(filters['exam_type']))
        
        # Executăm query-ul
        courses = query.all()
        
        # Serializăm rezultatele
        result = []
        for course in courses:
            result.append({
                'id': course.id,
                'code': course.code,
                'name': course.name,
                'faculty': course.faculty,
                'department': course.department,
                'study_program': course.study_program,
                'year_of_study': course.year_of_study,
                'semester': course.semester,
                'credits': course.credits,
                'group_name': course.group_name,
                'exam_type': course.exam_type.value,
                'teacher': {
                    'id': course.teacher.id if course.teacher else None,
                    'name': f"{course.teacher.academic_title or ''} {course.teacher.first_name} {course.teacher.last_name}".strip() if course.teacher else None,
                    'email': course.teacher.email if course.teacher else None
                },
                'assistant': {
                    'id': course.assistant.id if course.assistant else None,
                    'name': f"{course.assistant.academic_title or ''} {course.assistant.first_name} {course.assistant.last_name}".strip() if course.assistant else None,
                    'email': course.assistant.email if course.assistant else None
                } if course.assistant_id else None,
                'status': course.status,
                'proposed_date': course.proposed_date.isoformat() if course.proposed_date else None,
                'approved_date': course.approved_date.isoformat() if course.approved_date else None,
                'exam_room': {
                    'id': course.exam_room.id,
                    'name': course.exam_room.name
                } if course.exam_room else None,
                'exam_duration': course.exam_duration
            })
        
        return result
    except Exception as e:
        logger.error(f"Error in get_courses_data: {str(e)}")
        return []

@course_bp.route('/', methods=['GET'])
@jwt_required()
def get_courses():
    """
    Obține lista disciplinelor cu opțiuni de filtrare
    
    Query params:
        faculty (str): Filtrare după facultate
        department (str): Filtrare după departament
        study_program (str): Filtrare după program de studiu
        year_of_study (int): Filtrare după an de studiu
        semester (str): Filtrare după semestru
        group_name (str): Filtrare după grupă
        exam_type (str): Filtrare după tip examen (exam, colloquium, project)
    """
    try:
        # Preluăm parametrii din query string pentru filtrare
        filters = {
            'faculty': request.args.get('faculty'),
            'department': request.args.get('department'),
            'study_program': request.args.get('study_program'),
            'year_of_study': request.args.get('year_of_study'),
            'semester': request.args.get('semester'),
            'group_name': request.args.get('group_name'),
            'exam_type': request.args.get('exam_type')
        }
        
        # Folosim funcția utilitară pentru a obține datele
        result = get_courses_data(filters)
        
        # Asigurăm formatul corect pentru frontend
        # Verificăm dacă există date și trimitem un mesaj corespunzător
        if not result:
            message = "Nu există discipline încă. Încărcați un fișier sau sincronizați cu Orar."
        else:
            message = f"Au fost găsite {len(result)} discipline."
            
        return jsonify({
            'status': 'success',
            'message': message,
            'data': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting courses: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve courses',
            'error': str(e)
        }), 500


@course_bp.route('/sync', methods=['POST'])
@jwt_required()
def sync_courses():
    """
    Sincronizează disciplinele din sistemul Orar
    
    Body params:
        faculty (str): Facultatea pentru care se sincronizează disciplinele
        study_program (str, optional): Program de studiu specific
        year_of_study (int, optional): An de studiu specific
        semester (str, optional): Semestru specific
        group_name (str, optional): Grupă specifică
    """
    try:
        data = request.get_json()
        
        # Verificăm parametrii obligatorii
        if not data or 'faculty' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Faculty parameter is required'
            }), 400
        
        # Extragem parametrii
        faculty = data.get('faculty')
        study_program = data.get('study_program')
        year_of_study = data.get('year_of_study')
        semester = data.get('semester')
        group_name = data.get('group_name')
        
        # Obținem disciplinele de la API-ul Orar
        disciplines = orar_client.get_disciplines(
            faculty=faculty,
            program=study_program,
            year=year_of_study,
            semester=semester,
            group=group_name
        )
        
        # Dacă nu există discipline, returnăm eroare
        if not disciplines:
            return jsonify({
                'status': 'error',
                'message': 'No disciplines found for the specified criteria'
            }), 404
        
        # Procesăm fiecare disciplină
        sync_results = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'total': len(disciplines)
        }
        
        for disc in disciplines:
            try:
                # Verificăm dacă există deja disciplina în baza de date
                existing_course = Course.query.filter_by(code=disc['code'], group_name=disc['group_name']).first()
                
                # Găsim profesorul în baza de date după email
                teacher = None
                if 'teacher' in disc and 'email' in disc['teacher']:
                    teacher = User.query.filter_by(email=disc['teacher']['email']).first()
                
                # Dacă nu există cursul, îl creăm
                if not existing_course:
                    new_course = Course(
                        code=disc['code'],
                        name=disc['name'],
                        faculty=disc['faculty'],
                        department=disc.get('department'),
                        study_program=disc['study_program'],
                        year_of_study=disc['year_of_study'],
                        semester=disc['semester'],
                        credits=disc.get('credits'),
                        group_name=disc['group_name'],
                        exam_type=ExamType(disc.get('exam_type', 'exam')),
                        teacher_id=teacher.id if teacher else None
                    )
                    db.session.add(new_course)
                    sync_results['created'] += 1
                else:
                    # Actualizăm cursul existent
                    existing_course.name = disc['name']
                    existing_course.faculty = disc['faculty']
                    existing_course.department = disc.get('department')
                    existing_course.study_program = disc['study_program']
                    existing_course.year_of_study = disc['year_of_study']
                    existing_course.semester = disc['semester']
                    existing_course.credits = disc.get('credits')
                    existing_course.exam_type = ExamType(disc.get('exam_type', 'exam'))
                    
                    # Actualizăm profesorul doar dacă nu a fost deja setat sau respins/aprobat
                    if not existing_course.teacher_id and teacher:
                        existing_course.teacher_id = teacher.id
                    
                    sync_results['updated'] += 1
            
            except Exception as e:
                logger.error(f"Error syncing course {disc.get('code', 'unknown')}: {str(e)}")
                sync_results['errors'] += 1
        
        # Salvăm modificările în baza de date
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Courses synchronized successfully',
            'results': sync_results
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing courses: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to synchronize courses',
            'error': str(e)
        }), 500


@course_bp.route('/<int:course_id>', methods=['GET'])
@jwt_required()
def get_course(course_id):
    """
    Obține detaliile unei discipline specifice
    
    Path params:
        course_id (int): ID-ul disciplinei
    """
    try:
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({
                'status': 'error',
                'message': f'Course with ID {course_id} not found'
            }), 404
        
        # Serializăm rezultatul
        result = {
            'id': course.id,
            'code': course.code,
            'name': course.name,
            'faculty': course.faculty,
            'department': course.department,
            'study_program': course.study_program,
            'year_of_study': course.year_of_study,
            'semester': course.semester,
            'credits': course.credits,
            'group_name': course.group_name,
            'exam_type': course.exam_type.value,
            'teacher': {
                'id': course.teacher.id if course.teacher else None,
                'name': f"{course.teacher.academic_title or ''} {course.teacher.first_name} {course.teacher.last_name}".strip() if course.teacher else None,
                'email': course.teacher.email if course.teacher else None
            },
            'assistant': {
                'id': course.assistant.id if course.assistant else None,
                'name': f"{course.assistant.academic_title or ''} {course.assistant.first_name} {course.assistant.last_name}".strip() if course.assistant else None,
                'email': course.assistant.email if course.assistant else None
            } if course.assistant_id else None,
            'status': course.status,
            'proposed_date': course.proposed_date.isoformat() if course.proposed_date else None,
            'approved_date': course.approved_date.isoformat() if course.approved_date else None,
            'exam_room': {
                'id': course.exam_room.id,
                'name': course.exam_room.name
            } if course.exam_room else None,
            'exam_duration': course.exam_duration
        }
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting course {course_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve course with ID {course_id}',
            'error': str(e)
        }), 500


@course_bp.route('/<int:course_id>/propose-date', methods=['POST'])
@jwt_required()
def propose_exam_date(course_id):
    """
    Propune o dată pentru examen
    
    Path params:
        course_id (int): ID-ul disciplinei
        
    Body params:
        proposed_date (str): Data propusă pentru examen (format ISO: YYYY-MM-DDTHH:MM:SS)
    """
    try:
        # Verificăm dacă există disciplina
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({
                'status': 'error',
                'message': f'Course with ID {course_id} not found'
            }), 404
        
        # Verificăm dacă există deja o dată aprobată
        if course.status == 'approved':
            return jsonify({
                'status': 'error',
                'message': 'Exam date already approved and cannot be changed'
            }), 400
        
        # Extragem data propusă din request
        data = request.get_json()
        
        if not data or 'proposed_date' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Proposed date is required'
            }), 400
        
        # Convertim string-ul la obiect datetime
        try:
            proposed_date = datetime.fromisoformat(data['proposed_date'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid date format. Use ISO format: YYYY-MM-DDTHH:MM:SS'
            }), 400
        
        # Actualizăm disciplina
        course.proposed_date = proposed_date
        course.status = 'pending'
        course.updated_at = datetime.utcnow()
        
        # Salvăm modificările în baza de date
        db.session.commit()
        
        # Trimitem notificare prin email către profesor
        try:
            send_exam_proposal_notification(course)
        except Exception as email_error:
            logger.error(f"Error sending email notification: {str(email_error)}")
            # Continuăm execuția chiar dacă trimiterea emailului eșuează
        
        return jsonify({
            'status': 'success',
            'message': 'Exam date proposed successfully',
            'data': {
                'course_id': course.id,
                'course_name': course.name,
                'proposed_date': course.proposed_date.isoformat(),
                'status': course.status
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error proposing exam date for course {course_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to propose exam date for course with ID {course_id}',
            'error': str(e)
        }), 500


@course_bp.route('/<int:course_id>/review-proposal', methods=['POST'])
@jwt_required()
def review_exam_proposal(course_id):
    """
    Aprobă sau respinge o propunere de dată pentru examen
    
    Path params:
        course_id (int): ID-ul disciplinei
        
    Body params:
        action (str): "approve" sau "reject"
        rejection_reason (str, optional): Motivul respingerii (obligatoriu dacă action=reject)
        exam_room_id (int, optional): ID-ul sălii de examen (obligatoriu dacă action=approve)
        exam_duration (int, optional): Durata examenului în ore (obligatoriu dacă action=approve)
        assistant_id (int, optional): ID-ul asistentului pentru examen
    """
    try:
        # Verificăm dacă există disciplina
        course = Course.query.get(course_id)
        
        if not course:
            return jsonify({
                'status': 'error',
                'message': f'Course with ID {course_id} not found'
            }), 404
        
        # Verificăm dacă există o propunere în așteptare
        if course.status != 'pending':
            return jsonify({
                'status': 'error',
                'message': 'No pending proposal for this course'
            }), 400
        
        # Extragem datele din request
        data = request.get_json()
        
        if not data or 'action' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Action is required (approve or reject)'
            }), 400
        
        action = data.get('action')
        
        # Verificăm dacă acțiunea este validă
        if action not in ['approve', 'reject']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid action. Use "approve" or "reject"'
            }), 400
        
        # Procesăm acțiunea
        if action == 'approve':
            # Verificăm parametrii obligatorii pentru aprobare
            if 'exam_room_id' not in data:
                return jsonify({
                    'status': 'error',
                    'message': 'Exam room is required for approval'
                }), 400
                
            if 'exam_duration' not in data:
                return jsonify({
                    'status': 'error',
                    'message': 'Exam duration is required for approval'
                }), 400
            
            # Actualizăm disciplina
            course.status = 'approved'
            course.approved_date = course.proposed_date
            course.exam_room_id = data.get('exam_room_id')
            course.exam_duration = data.get('exam_duration')
            
            # Adăugăm asistentul dacă este specificat
            if 'assistant_id' in data:
                course.assistant_id = data.get('assistant_id')
            
            message = 'Exam proposal approved successfully'
            
        elif action == 'reject':
            # Verificăm motivul respingerii
            if 'rejection_reason' not in data or not data.get('rejection_reason'):
                return jsonify({
                    'status': 'error',
                    'message': 'Rejection reason is required'
                }), 400
            
            # Actualizăm disciplina
            course.status = 'rejected'
            course.rejection_reason = data.get('rejection_reason')
            course.proposed_date = None
            
            message = 'Exam proposal rejected'
        
        # Actualizăm timestamp-ul
        course.updated_at = datetime.utcnow()
        
        # Salvăm modificările în baza de date
        db.session.commit()
        
        # Trimitem notificare prin email
        try:
            if action == 'approve':
                send_exam_approval_notification(course)
            elif action == 'reject':
                send_exam_rejection_notification(course)
        except Exception as email_error:
            logger.error(f"Error sending email notification: {str(email_error)}")
            # Continuăm execuția chiar dacă trimiterea emailului eșuează
        
        return jsonify({
            'status': 'success',
            'message': message,
            'data': {
                'course_id': course.id,
                'course_name': course.name,
                'status': course.status,
                'approved_date': course.approved_date.isoformat() if course.approved_date else None,
                'rejection_reason': course.rejection_reason
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error reviewing exam proposal for course {course_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to review exam proposal for course with ID {course_id}',
            'error': str(e)
        }), 500
