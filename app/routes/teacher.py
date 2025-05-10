from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app.models.user import User, UserRole
from app.models.room import Room
from app.models.schedule import Schedule, DayOfWeek
from app.models.reservation import Reservation, ReservationStatus
from app.models.settings import InstitutionSettings
from app import db
from app.utils.email_service import send_approval_notification, send_rejection_notification
from sqlalchemy import and_, or_, func

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.route('/exam-proposals', methods=['GET'])
@jwt_required()
def get_exam_proposals():
    """Get all pending exam proposals for the teacher"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get proposals where the teacher is assigned
    proposals = Reservation.query.filter(
        Reservation.status == ReservationStatus.PENDING,
        Reservation.purpose.like('%examen%') | Reservation.purpose.like('%colocviu%')
    ).all()
    
    # Format proposals for frontend
    formatted_proposals = []
    for proposal in proposals:
        student = User.query.get(proposal.user_id)
        room = Room.query.get(proposal.room_id)
        
        # Extract discipline name from purpose
        purpose_parts = proposal.purpose.split(' de ')
        discipline_name = purpose_parts[1] if len(purpose_parts) > 1 else proposal.purpose
        
        # Determine exam type
        exam_type = 'examen' if 'examen' in proposal.purpose.lower() else 'colocviu'
        
        formatted_proposals.append({
            'id': proposal.id,
            'disciplineName': discipline_name,
            'group': student.group if hasattr(student, 'group') else 'N/A',
            'year': student.year if hasattr(student, 'year') else 'N/A',
            'groupLeader': student.full_name,
            'groupLeaderEmail': student.email,
            'examType': exam_type,
            'proposedDate': proposal.date.strftime('%Y-%m-%d'),
            'status': proposal.status.value,
            'rejectionReason': proposal.rejection_reason
        })
    
    return jsonify({
        'proposals': formatted_proposals
    }), 200

@teacher_bp.route('/approved-exams', methods=['GET'])
@jwt_required()
def get_approved_exams():
    """Get all approved exams for the teacher"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get approved exams where the teacher is assigned
    exams = Reservation.query.filter(
        Reservation.status == ReservationStatus.APPROVED,
        Reservation.purpose.like('%examen%') | Reservation.purpose.like('%colocviu%')
    ).all()
    
    # Format exams for frontend
    formatted_exams = []
    for exam in exams:
        student = User.query.get(exam.user_id)
        room = Room.query.get(exam.room_id)
        
        # Extract discipline name from purpose
        purpose_parts = exam.purpose.split(' de ')
        discipline_name = purpose_parts[1] if len(purpose_parts) > 1 else exam.purpose
        
        # Determine exam type
        exam_type = 'examen' if 'examen' in exam.purpose.lower() else 'colocviu'
        
        formatted_exams.append({
            'id': exam.id,
            'disciplineName': discipline_name,
            'group': student.group if hasattr(student, 'group') else 'N/A',
            'year': student.year if hasattr(student, 'year') else 'N/A',
            'groupLeader': student.full_name,
            'groupLeaderEmail': student.email,
            'examType': exam_type,
            'proposedDate': exam.date.strftime('%Y-%m-%d'),
            'status': exam.status.value,
            'room': room.name if room else '',
            'startTime': exam.start_time.strftime('%H:%M') if exam.start_time else '',
            'endTime': exam.end_time.strftime('%H:%M') if exam.end_time else '',
            'assistants': []  # This would be populated from a separate assistants table
        })
    
    return jsonify({
        'exams': formatted_exams
    }), 200

@teacher_bp.route('/available-rooms', methods=['GET'])
@jwt_required()
def get_available_rooms():
    """Get all available rooms"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get all active rooms
    rooms = Room.query.filter_by(is_active=True).all()
    
    # Format rooms for frontend
    formatted_rooms = []
    for room in rooms:
        formatted_rooms.append({
            'id': room.id,
            'name': room.name,
            'capacity': room.capacity,
            'building': room.building,
            'floor': room.floor,
            'available': True  # We could implement more complex availability logic here
        })
    
    return jsonify({
        'rooms': formatted_rooms
    }), 200

@teacher_bp.route('/available-assistants', methods=['GET'])
@jwt_required()
def get_available_assistants():
    """Get all available assistants"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get all users who could be assistants (teachers, assistants, etc.)
    assistants = User.query.filter(
        User.role == UserRole.TEACHER,
        User.is_active == True
    ).all()
    
    # Format assistants for frontend
    formatted_assistants = []
    for assistant in assistants:
        formatted_assistants.append({
            'id': assistant.id,
            'name': f"{assistant.academic_title or ''} {assistant.full_name}",
            'email': assistant.email,
            'available': True  # We could implement more complex availability logic here
        })
    
    return jsonify({
        'assistants': formatted_assistants
    }), 200

@teacher_bp.route('/exam-proposals/<int:proposal_id>/approve', methods=['PUT'])
@jwt_required()
def approve_exam_proposal(proposal_id):
    """Approve an exam proposal"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    proposal = Reservation.query.get(proposal_id)
    
    if not proposal:
        return jsonify({'message': 'Propunere negăsită'}), 404
    
    if proposal.status != ReservationStatus.PENDING:
        return jsonify({'message': 'Doar propunerile în așteptare pot fi aprobate'}), 400
    
    # Approve the proposal
    proposal.approve(user.id)
    db.session.commit()
    
    # Send notification to student
    send_approval_notification(proposal)
    
    return jsonify({
        'message': 'Propunerea a fost aprobată cu succes',
        'success': True
    }), 200

@teacher_bp.route('/exam-proposals/<int:proposal_id>/reject', methods=['PUT'])
@jwt_required()
def reject_exam_proposal(proposal_id):
    """Reject an exam proposal"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    proposal = Reservation.query.get(proposal_id)
    
    if not proposal:
        return jsonify({'message': 'Propunere negăsită'}), 404
    
    if proposal.status != ReservationStatus.PENDING:
        return jsonify({'message': 'Doar propunerile în așteptare pot fi respinse'}), 400
    
    data = request.get_json()
    
    if not data or not data.get('reason'):
        return jsonify({'message': 'Motivul respingerii este obligatoriu'}), 400
    
    # Reject the proposal
    proposal.reject(user.id, data.get('reason'))
    db.session.commit()
    
    # Send notification to student
    send_rejection_notification(proposal)
    
    return jsonify({
        'message': 'Propunerea a fost respinsă cu succes',
        'success': True
    }), 200

@teacher_bp.route('/exams/<int:exam_id>', methods=['PUT'])
@jwt_required()
def update_exam_details(exam_id):
    """Update exam details (room, time, assistants)"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    exam = Reservation.query.get(exam_id)
    
    if not exam:
        return jsonify({'message': 'Examen negăsit'}), 404
    
    if exam.status != ReservationStatus.APPROVED:
        return jsonify({'message': 'Doar examenele aprobate pot fi actualizate'}), 400
    
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'Date lipsă'}), 400
    
    # Update room
    if 'room_id' in data and data['room_id']:
        room = Room.query.get(data['room_id'])
        if not room:
            return jsonify({'message': 'Sala specificată nu există'}), 404
        exam.room_id = room.id
    
    # Update time
    if 'start_time' in data and data['start_time']:
        try:
            start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            exam.start_time = start_time
        except ValueError:
            return jsonify({'message': 'Format de timp invalid pentru ora de început'}), 400
    
    if 'end_time' in data and data['end_time']:
        try:
            end_time = datetime.strptime(data['end_time'], '%H:%M').time()
            exam.end_time = end_time
        except ValueError:
            return jsonify({'message': 'Format de timp invalid pentru ora de sfârșit'}), 400
    
    # Update assistants - this would require a separate table for assistants
    # For now, we'll just store the assistant information in the notes field
    if 'assistants' in data:
        assistants_str = ', '.join(data['assistants'])
        exam.notes = f"{exam.notes or ''}\nAsistenți: {assistants_str}"
    
    db.session.commit()
    
    return jsonify({
        'message': 'Detaliile examenului au fost actualizate cu succes',
        'success': True,
        'exam': exam.to_dict()
    }), 200
