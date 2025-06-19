"""
API endpoints pentru managementul profesorilor
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models.user import User, UserRole
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Creăm un Blueprint pentru managementul profesorilor
teacher_management_bp = Blueprint('teacher_management', __name__, url_prefix='/api/teacher-management')

@teacher_management_bp.route('/add-teacher', methods=['POST'])
@jwt_required()
def add_teacher():
    """
    Adaugă un profesor în baza de date
    
    Body params:
        email (str): Email-ul profesorului
        first_name (str): Prenumele profesorului
        last_name (str): Numele profesorului
        academic_title (str, optional): Titlul academic
    """
    try:
        # Verificăm dacă utilizatorul este admin
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Pentru testare, permitem oricui să adauge profesori
        # if current_user.role != UserRole.ADMIN:
        #     return jsonify({
        #         'status': 'error',
        #         'message': 'Doar administratorii pot adăuga profesori'
        #     }), 403
        
        # Obținem datele din request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Nu s-au furnizat date'
            }), 400
        
        # Validăm datele obligatorii
        required_fields = ['email', 'first_name', 'last_name']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'status': 'error',
                    'message': f'Câmpul {field} este obligatoriu'
                }), 400
        
        # Verificăm dacă profesorul există deja
        existing_teacher = User.query.filter_by(email=data['email']).first()
        if existing_teacher:
            # Actualizăm datele profesorului
            existing_teacher.first_name = data['first_name']
            existing_teacher.last_name = data['last_name']
            existing_teacher.academic_title = data.get('academic_title', '')
            existing_teacher.is_active = True
            existing_teacher.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Profesorul a fost actualizat cu succes',
                'data': {
                    'id': existing_teacher.id,
                    'email': existing_teacher.email,
                    'name': f"{existing_teacher.academic_title or ''} {existing_teacher.first_name} {existing_teacher.last_name}".strip()
                }
            }), 200
        
        # Creăm un nou profesor
        new_teacher = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            academic_title=data.get('academic_title', ''),
            role=UserRole.TEACHER,
            is_active=True
        )
        
        # Setăm o parolă temporară (pentru testare)
        new_teacher.set_password('password123')
        
        # Salvăm în baza de date
        db.session.add(new_teacher)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Profesorul a fost adăugat cu succes',
            'data': {
                'id': new_teacher.id,
                'email': new_teacher.email,
                'name': f"{new_teacher.academic_title or ''} {new_teacher.first_name} {new_teacher.last_name}".strip()
            }
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Eroare la salvarea în baza de date',
            'error': str(e)
        }), 500
    except Exception as e:
        logger.error(f"Error adding teacher: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Eroare la adăugarea profesorului',
            'error': str(e)
        }), 500

@teacher_management_bp.route('/add-exam-proposal', methods=['POST'])
@jwt_required()
def add_exam_proposal():
    """
    Adaugă o propunere de examen pentru un profesor
    
    Body params:
        course_id (int): ID-ul cursului
        proposed_date (str): Data propusă pentru examen (format: YYYY-MM-DD)
        proposed_time (str): Ora propusă pentru examen (format: HH:MM)
    """
    try:
        # Obținem datele din request
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Nu s-au furnizat date'
            }), 400
        
        # Validăm datele obligatorii
        required_fields = ['course_id', 'proposed_date', 'proposed_time']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'status': 'error',
                    'message': f'Câmpul {field} este obligatoriu'
                }), 400
        
        # Obținem cursul
        from app.models.course import Course
        course = Course.query.get(data['course_id'])
        
        if not course:
            return jsonify({
                'status': 'error',
                'message': f'Cursul cu ID-ul {data["course_id"]} nu există'
            }), 404
        
        # Formatăm data și ora
        from datetime import datetime
        proposed_datetime_str = f"{data['proposed_date']}T{data['proposed_time']}:00"
        proposed_datetime = datetime.fromisoformat(proposed_datetime_str)
        
        # Actualizăm cursul cu data propusă
        course.proposed_date = proposed_datetime
        course.status = 'pending'
        
        # Salvăm în baza de date
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Propunerea de examen a fost adăugată cu succes',
            'data': {
                'course_id': course.id,
                'course_name': course.name,
                'proposed_date': proposed_datetime.isoformat(),
                'status': course.status
            }
        }), 201
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'message': 'Format invalid pentru dată sau oră',
            'error': str(e)
        }), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Eroare la salvarea în baza de date',
            'error': str(e)
        }), 500
    except Exception as e:
        logger.error(f"Error adding exam proposal: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Eroare la adăugarea propunerii de examen',
            'error': str(e)
        }), 500
