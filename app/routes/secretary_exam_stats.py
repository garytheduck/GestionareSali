from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User, UserRole
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room
from app import db
from sqlalchemy import func

# Acest endpoint va fi adăugat în secretary.py
# Îl creăm separat pentru a putea fi testat și apoi integrat

@jwt_required()
def get_exam_stats():
    """Get statistics about exams (total, completed, incomplete)"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get all exam/colloquium reservations
    exams = Reservation.query.filter(
        Reservation.purpose.like('%examen%') | Reservation.purpose.like('%colocviu%')
    ).all()
    
    # Count total and completed
    total = len(exams)
    completed = sum(1 for exam in exams if exam.status == ReservationStatus.APPROVED)
    
    # Get incomplete exams
    incomplete_exams = []
    for exam in exams:
        if exam.status != ReservationStatus.APPROVED:
            student = User.query.get(exam.user_id)
            
            # Extract discipline name from purpose
            purpose_parts = exam.purpose.split(' de ')
            discipline_name = purpose_parts[1] if len(purpose_parts) > 1 else exam.purpose
            
            incomplete_exams.append({
                'id': exam.id,
                'name': discipline_name,
                'group': student.group if hasattr(student, 'group') else 'N/A',
                'status': exam.status.value
            })
    
    return jsonify({
        'total': total,
        'completed': completed,
        'incomplete': incomplete_exams
    }), 200
