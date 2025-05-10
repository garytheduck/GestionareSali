from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app.models.user import User, UserRole
from app.models.reservation import Reservation, ReservationStatus
from app.models.room import Room
from app import db
from app.utils.email_service import send_approval_notification, send_rejection_notification
from app.utils.report_generator import generate_reservations_report
import io
import os

secretary_bp = Blueprint('secretary', __name__)

@secretary_bp.route('/reservations/pending', methods=['GET'])
@jwt_required()
def get_pending_reservations():
    """Get all pending reservations"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get query parameters
    room_id = request.args.get('room_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build query
    query = Reservation.query.filter(Reservation.status == ReservationStatus.PENDING)
    
    # Apply filters
    if room_id:
        query = query.filter(Reservation.room_id == room_id)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Reservation.date >= date_from_obj)
        except ValueError:
            pass  # Ignore invalid date
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Reservation.date <= date_to_obj)
        except ValueError:
            pass  # Ignore invalid date
    
    # Order by date and time
    query = query.order_by(Reservation.date.asc(), Reservation.start_time.asc())
    
    reservations = query.all()
    
    return jsonify({
        'reservations': [reservation.to_dict() for reservation in reservations]
    }), 200

@secretary_bp.route('/reservations/<int:reservation_id>/approve', methods=['PUT'])
@jwt_required()
def approve_reservation(reservation_id):
    """Approve a pending reservation"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({'message': 'Rezervare negăsită'}), 404
    
    if reservation.status != ReservationStatus.PENDING:
        return jsonify({'message': 'Doar rezervările în așteptare pot fi aprobate'}), 400
    
    # Approve the reservation
    reservation.approve(user.id)
    db.session.commit()
    
    # Send notification to student
    send_approval_notification(reservation)
    
    return jsonify({
        'message': 'Rezervarea a fost aprobată cu succes',
        'reservation': reservation.to_dict()
    }), 200

@secretary_bp.route('/reservations/<int:reservation_id>/reject', methods=['PUT'])
@jwt_required()
def reject_reservation(reservation_id):
    """Reject a pending reservation"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({'message': 'Rezervare negăsită'}), 404
    
    if reservation.status != ReservationStatus.PENDING:
        return jsonify({'message': 'Doar rezervările în așteptare pot fi respinse'}), 400
    
    data = request.get_json()
    
    if not data or not data.get('rejection_reason'):
        return jsonify({'message': 'Motivul respingerii este obligatoriu'}), 400
    
    # Reject the reservation
    reservation.reject(user.id, data.get('rejection_reason'))
    db.session.commit()
    
    # Send notification to student
    send_rejection_notification(reservation)
    
    return jsonify({
        'message': 'Rezervarea a fost respinsă',
        'reservation': reservation.to_dict()
    }), 200

@secretary_bp.route('/reservations/<int:reservation_id>/edit', methods=['PUT'])
@jwt_required()
def edit_reservation(reservation_id):
    """Edit a reservation (for corrections)"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({'message': 'Rezervare negăsită'}), 404
    
    data = request.get_json()
    
    # Update allowed fields
    if data.get('room_id'):
        room = Room.query.get(data.get('room_id'))
        if not room or not room.is_active:
            return jsonify({'message': 'Sala nu a fost găsită sau este inactivă'}), 404
        reservation.room_id = room.id
    
    if data.get('purpose'):
        reservation.purpose = data.get('purpose')
    
    if data.get('date'):
        try:
            date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
            reservation.date = date
        except ValueError:
            return jsonify({'message': 'Format de dată invalid'}), 400
    
    if data.get('start_time'):
        try:
            start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
            reservation.start_time = start_time
        except ValueError:
            return jsonify({'message': 'Format de oră invalid'}), 400
    
    if data.get('end_time'):
        try:
            end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
            reservation.end_time = end_time
        except ValueError:
            return jsonify({'message': 'Format de oră invalid'}), 400
    
    # Validate start time is before end time
    if reservation.start_time >= reservation.end_time:
        return jsonify({'message': 'Ora de început trebuie să fie înainte de ora de sfârșit'}), 400
    
    db.session.commit()
    
    return jsonify({
        'message': 'Rezervarea a fost actualizată cu succes',
        'reservation': reservation.to_dict()
    }), 200

@secretary_bp.route('/reservations/history', methods=['GET'])
@jwt_required()
def get_reservation_history():
    """Get reservation history with filters"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get query parameters
    status = request.args.get('status')
    room_id = request.args.get('room_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query
    query = Reservation.query
    
    # Apply filters
    if status:
        try:
            status_enum = ReservationStatus(status)
            query = query.filter(Reservation.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status
    
    if room_id:
        query = query.filter(Reservation.room_id == room_id)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(Reservation.date >= date_from_obj)
        except ValueError:
            pass  # Ignore invalid date
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(Reservation.date <= date_to_obj)
        except ValueError:
            pass  # Ignore invalid date
    
    # Order by date and time
    query = query.order_by(Reservation.date.desc(), Reservation.start_time.desc())
    
    # Paginate results
    paginated_reservations = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'reservations': [reservation.to_dict() for reservation in paginated_reservations.items],
        'total': paginated_reservations.total,
        'pages': paginated_reservations.pages,
        'current_page': page
    }), 200

@secretary_bp.route('/reports/daily', methods=['GET'])
@jwt_required()
def generate_daily_report():
    """Generate a daily report of reservations"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get date parameter, default to today
    date_str = request.args.get('date')
    
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'message': 'Format de dată invalid. Folosiți YYYY-MM-DD'}), 400
    else:
        date = datetime.now().date()
    
    # Generate report
    report_bytes = generate_reservations_report(date, date)
    
    # Create in-memory file
    report_io = io.BytesIO(report_bytes)
    report_io.seek(0)
    
    # Generate filename
    filename = f"rezervari_{date.strftime('%Y-%m-%d')}.xlsx"
    
    return send_file(
        report_io,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@secretary_bp.route('/reports/period', methods=['GET'])
@jwt_required()
def generate_period_report():
    """Generate a report for a specific period"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in [UserRole.SECRETARY, UserRole.ADMIN]:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get date parameters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if not date_from or not date_to:
        return jsonify({'message': 'Parametrii date_from și date_to sunt obligatorii'}), 400
    
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'message': 'Format de dată invalid. Folosiți YYYY-MM-DD'}), 400
    
    # Generate report
    report_bytes = generate_reservations_report(date_from_obj, date_to_obj)
    
    # Create in-memory file
    report_io = io.BytesIO(report_bytes)
    report_io.seek(0)
    
    # Generate filename
    filename = f"rezervari_{date_from_obj.strftime('%Y-%m-%d')}_{date_to_obj.strftime('%Y-%m-%d')}.xlsx"
    
    return send_file(
        report_io,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@secretary_bp.route('/exam-stats', methods=['GET'])
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
