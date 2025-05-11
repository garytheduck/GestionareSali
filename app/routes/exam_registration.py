"""
API endpoints pentru înscrierea studenților la examene
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.exam import Exam, ExamRegistration
from app.models import User
from werkzeug.exceptions import BadRequest, NotFound
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Creăm un Blueprint pentru înscrierea la examene
registration_bp = Blueprint('registration', __name__, url_prefix='/api/exam-registrations')

@registration_bp.route('/', methods=['GET'])
@jwt_required()
def get_registrations():
    """
    Obține lista înregistrărilor la examene pentru utilizatorul curent
    
    Query params:
        exam_id (int): Filtrare după ID-ul examenului
        status (str): Filtrare după status (registered, confirmed, cancelled, attended, etc.)
    """
    try:
        # Obținem ID-ul utilizatorului curent
        current_user_id = get_jwt_identity()
        
        # Obținem utilizatorul curent
        current_user = User.query.get(current_user_id)
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Preluăm parametrii din query string
        exam_id = request.args.get('exam_id')
        status = request.args.get('status')
        
        # Construim query-ul
        query = ExamRegistration.query.filter(ExamRegistration.student_id == current_user_id)
        
        if exam_id:
            query = query.filter(ExamRegistration.exam_id == int(exam_id))
        if status:
            query = query.filter(ExamRegistration.status == status)
        
        # Executăm query-ul
        registrations = query.all()
        
        # Serializăm rezultatele
        result = []
        for reg in registrations:
            result.append({
                'id': reg.id,
                'exam': {
                    'id': reg.exam.id,
                    'course': {
                        'id': reg.exam.course.id,
                        'name': reg.exam.course.name,
                        'code': reg.exam.course.code
                    },
                    'room': {
                        'id': reg.exam.room.id,
                        'name': reg.exam.room.name,
                        'building': reg.exam.room.building
                    },
                    'start_time': reg.exam.start_time.isoformat(),
                    'end_time': reg.exam.end_time.isoformat(),
                    'exam_type': reg.exam.exam_type,
                    'semester': reg.exam.semester,
                    'academic_year': reg.exam.academic_year
                },
                'status': reg.status,
                'registration_time': reg.registration_time.isoformat(),
                'notes': reg.notes,
                'created_at': reg.created_at.isoformat() if reg.created_at else None,
                'updated_at': reg.updated_at.isoformat() if reg.updated_at else None
            })
        
        return jsonify({
            'status': 'success',
            'data': result,
            'count': len(result)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting registrations: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve registrations',
            'error': str(e)
        }), 500


@registration_bp.route('/', methods=['POST'])
@jwt_required()
def register_for_exam():
    """
    Înregistrează utilizatorul curent la un examen
    
    Body params:
        exam_id (int): ID-ul examenului
        notes (str, optional): Note sau observații
    """
    try:
        # Obținem ID-ul utilizatorului curent
        current_user_id = get_jwt_identity()
        
        # Obținem utilizatorul curent
        current_user = User.query.get(current_user_id)
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Preluăm datele din corpul cererii
        data = request.get_json()
        
        # Verificăm câmpurile obligatorii
        if 'exam_id' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: exam_id'
            }), 400
        
        # Verificăm dacă examenul există
        exam = Exam.query.get(data['exam_id'])
        if not exam or not exam.is_active:
            return jsonify({
                'status': 'error',
                'message': f'Exam with ID {data["exam_id"]} not found'
            }), 404
        
        # Verificăm dacă examenul nu a trecut deja
        if exam.start_time < datetime.utcnow():
            return jsonify({
                'status': 'error',
                'message': 'Cannot register for an exam that has already started or ended'
            }), 400
        
        # Verificăm dacă utilizatorul este deja înregistrat la acest examen
        existing_registration = ExamRegistration.query.filter(
            and_(
                ExamRegistration.exam_id == data['exam_id'],
                ExamRegistration.student_id == current_user_id,
                ExamRegistration.status != 'cancelled'
            )
        ).first()
        
        if existing_registration:
            return jsonify({
                'status': 'error',
                'message': 'You are already registered for this exam',
                'registration': {
                    'id': existing_registration.id,
                    'status': existing_registration.status,
                    'registration_time': existing_registration.registration_time.isoformat()
                }
            }), 409  # Conflict
        
        # Verificăm capacitatea maximă a examenului (dacă este specificată)
        if exam.max_students:
            current_registrations = ExamRegistration.query.filter(
                and_(
                    ExamRegistration.exam_id == data['exam_id'],
                    ExamRegistration.status != 'cancelled'
                )
            ).count()
            
            if current_registrations >= exam.max_students:
                return jsonify({
                    'status': 'error',
                    'message': 'The exam has reached its maximum capacity'
                }), 409  # Conflict
        
        # Creăm înregistrarea
        registration = ExamRegistration(
            exam_id=data['exam_id'],
            student_id=current_user_id,
            status='registered',
            registration_time=datetime.utcnow(),
            notes=data.get('notes')
        )
        
        # Salvăm în baza de date
        db.session.add(registration)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Successfully registered for the exam',
            'data': {
                'id': registration.id,
                'exam': {
                    'id': exam.id,
                    'course_name': exam.course.name,
                    'start_time': exam.start_time.isoformat(),
                    'end_time': exam.end_time.isoformat(),
                    'room_name': exam.room.name
                },
                'status': registration.status,
                'registration_time': registration.registration_time.isoformat(),
                'notes': registration.notes
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error registering for exam: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to register for the exam',
            'error': str(e)
        }), 500


@registration_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_registration(id):
    """
    Obține detaliile unei înregistrări specifice
    
    Path params:
        id (int): ID-ul înregistrării
    """
    try:
        # Obținem ID-ul utilizatorului curent
        current_user_id = get_jwt_identity()
        
        # Obținem înregistrarea
        registration = ExamRegistration.query.get(id)
        
        if not registration:
            return jsonify({
                'status': 'error',
                'message': f'Registration with ID {id} not found'
            }), 404
        
        # Verificăm dacă înregistrarea aparține utilizatorului curent sau dacă utilizatorul este admin/secretariat
        current_user = User.query.get(current_user_id)
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        is_admin_or_secretary = current_user.role in ['admin', 'secretary']
        
        if registration.student_id != current_user_id and not is_admin_or_secretary:
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to view this registration'
            }), 403
        
        # Serializăm rezultatul
        result = {
            'id': registration.id,
            'exam': {
                'id': registration.exam.id,
                'course': {
                    'id': registration.exam.course.id,
                    'name': registration.exam.course.name,
                    'code': registration.exam.course.code
                },
                'room': {
                    'id': registration.exam.room.id,
                    'name': registration.exam.room.name,
                    'building': registration.exam.room.building
                },
                'start_time': registration.exam.start_time.isoformat(),
                'end_time': registration.exam.end_time.isoformat(),
                'exam_type': registration.exam.exam_type,
                'semester': registration.exam.semester,
                'academic_year': registration.exam.academic_year
            },
            'student': {
                'id': registration.student.id,
                'first_name': registration.student.first_name,
                'last_name': registration.student.last_name,
                'email': registration.student.email
            },
            'status': registration.status,
            'registration_time': registration.registration_time.isoformat(),
            'notes': registration.notes,
            'created_at': registration.created_at.isoformat() if registration.created_at else None,
            'updated_at': registration.updated_at.isoformat() if registration.updated_at else None
        }
        
        return jsonify({
            'status': 'success',
            'data': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting registration {id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve registration with ID {id}',
            'error': str(e)
        }), 500


@registration_bp.route('/<int:id>/cancel', methods=['PUT'])
@jwt_required()
def cancel_registration(id):
    """
    Anulează o înregistrare existentă
    
    Path params:
        id (int): ID-ul înregistrării
    """
    try:
        # Obținem ID-ul utilizatorului curent
        current_user_id = get_jwt_identity()
        
        # Obținem înregistrarea
        registration = ExamRegistration.query.get(id)
        
        if not registration:
            return jsonify({
                'status': 'error',
                'message': f'Registration with ID {id} not found'
            }), 404
        
        # Verificăm dacă înregistrarea aparține utilizatorului curent
        if registration.student_id != current_user_id:
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to cancel this registration'
            }), 403
        
        # Verificăm dacă examenul nu a trecut deja
        if registration.exam.start_time < datetime.utcnow():
            return jsonify({
                'status': 'error',
                'message': 'Cannot cancel registration for an exam that has already started or ended'
            }), 400
        
        # Verificăm dacă înregistrarea nu este deja anulată
        if registration.status == 'cancelled':
            return jsonify({
                'status': 'error',
                'message': 'Registration is already cancelled'
            }), 400
        
        # Actualizăm starea înregistrării
        registration.status = 'cancelled'
        registration.updated_at = datetime.utcnow()
        
        # Salvăm în baza de date
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Registration cancelled successfully',
            'data': {
                'id': registration.id,
                'status': registration.status,
                'updated_at': registration.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling registration {id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to cancel registration with ID {id}',
            'error': str(e)
        }), 500


@registration_bp.route('/exams/<int:exam_id>/students', methods=['GET'])
@jwt_required()
def get_exam_students(exam_id):
    """
    Obține lista studenților înscriși la un examen specific
    Doar pentru rolurile admin sau secretariat
    
    Path params:
        exam_id (int): ID-ul examenului
        
    Query params:
        status (str): Filtrare după status (registered, confirmed, cancelled, attended, etc.)
    """
    try:
        # Obținem ID-ul utilizatorului curent
        current_user_id = get_jwt_identity()
        
        # Obținem utilizatorul curent
        current_user = User.query.get(current_user_id)
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Verificăm dacă utilizatorul are rolul de admin sau secretariat
        if current_user.role not in ['admin', 'secretary']:
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to view this information'
            }), 403
        
        # Verificăm dacă examenul există
        exam = Exam.query.get(exam_id)
        if not exam or not exam.is_active:
            return jsonify({
                'status': 'error',
                'message': f'Exam with ID {exam_id} not found'
            }), 404
        
        # Preluăm parametrii din query string
        status = request.args.get('status')
        
        # Construim query-ul
        query = ExamRegistration.query.filter(ExamRegistration.exam_id == exam_id)
        
        if status:
            query = query.filter(ExamRegistration.status == status)
        
        # Executăm query-ul
        registrations = query.all()
        
        # Serializăm rezultatele
        result = []
        for reg in registrations:
            result.append({
                'id': reg.id,
                'student': {
                    'id': reg.student.id,
                    'first_name': reg.student.first_name,
                    'last_name': reg.student.last_name,
                    'email': reg.student.email
                },
                'status': reg.status,
                'registration_time': reg.registration_time.isoformat(),
                'notes': reg.notes
            })
        
        return jsonify({
            'status': 'success',
            'data': result,
            'count': len(result),
            'exam': {
                'id': exam.id,
                'course_name': exam.course.name,
                'start_time': exam.start_time.isoformat(),
                'end_time': exam.end_time.isoformat(),
                'room_name': exam.room.name
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting students for exam {exam_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve students for exam with ID {exam_id}',
            'error': str(e)
        }), 500


@registration_bp.route('/<int:id>/update-status', methods=['PUT'])
@jwt_required()
def update_registration_status(id):
    """
    Actualizează starea unei înregistrări
    Doar pentru rolurile admin sau secretariat
    
    Path params:
        id (int): ID-ul înregistrării
        
    Body params:
        status (str): Noua stare (registered, confirmed, cancelled, attended, etc.)
        notes (str, optional): Note sau observații
    """
    try:
        # Obținem ID-ul utilizatorului curent
        current_user_id = get_jwt_identity()
        
        # Obținem utilizatorul curent
        current_user = User.query.get(current_user_id)
        if not current_user:
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Verificăm dacă utilizatorul are rolul de admin sau secretariat
        if current_user.role not in ['admin', 'secretary']:
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to update registration status'
            }), 403
        
        # Preluăm datele din corpul cererii
        data = request.get_json()
        
        # Verificăm câmpurile obligatorii
        if 'status' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing required field: status'
            }), 400
        
        # Verificăm valorile permise pentru status
        allowed_statuses = ['registered', 'confirmed', 'cancelled', 'attended', 'no_show']
        if data['status'] not in allowed_statuses:
            return jsonify({
                'status': 'error',
                'message': f'Invalid status value. Allowed values: {", ".join(allowed_statuses)}'
            }), 400
        
        # Obținem înregistrarea
        registration = ExamRegistration.query.get(id)
        
        if not registration:
            return jsonify({
                'status': 'error',
                'message': f'Registration with ID {id} not found'
            }), 404
        
        # Actualizăm starea înregistrării
        registration.status = data['status']
        if 'notes' in data:
            registration.notes = data['notes']
        registration.updated_at = datetime.utcnow()
        
        # Salvăm în baza de date
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Registration status updated successfully',
            'data': {
                'id': registration.id,
                'status': registration.status,
                'notes': registration.notes,
                'updated_at': registration.updated_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating registration status {id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to update registration status with ID {id}',
            'error': str(e)
        }), 500
