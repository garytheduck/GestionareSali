from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from app.models.user import User, UserRole
from app.models.room import Room
from app.models.schedule import Schedule, DayOfWeek
from app.models.reservation import Reservation, ReservationStatus
from app.models.settings import InstitutionSettings
from app import db
from app.utils.email_service import send_reservation_notification
from app.utils.availability import check_room_availability
from sqlalchemy import and_, or_, func

student_bp = Blueprint('student', __name__)

@student_bp.route('/rooms', methods=['GET'])
@jwt_required()
def get_rooms():
    """Get all available rooms"""
    rooms = Room.query.filter_by(is_active=True).all()
    return jsonify({
        'rooms': [room.to_dict() for room in rooms]
    }), 200

@student_bp.route('/room/<int:room_id>/availability', methods=['GET'])
@jwt_required()
def get_room_availability(room_id):
    """Get room availability for a specific date"""
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'message': 'Data este obligatorie'}), 400
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'message': 'Format de dată invalid. Folosiți YYYY-MM-DD'}), 400
    
    room = Room.query.get(room_id)
    if not room or not room.is_active:
        return jsonify({'message': 'Sala nu a fost găsită sau este inactivă'}), 404
    
    # Get day of week for the given date
    day_of_week = DayOfWeek(date.strftime('%A').lower())
    
    # Get institution settings for working hours
    settings = InstitutionSettings.get_settings()
    
    # Get regular schedule for this room and day
    schedules = Schedule.query.filter(
        Schedule.room_id == room_id,
        Schedule.day_of_week == day_of_week,
        Schedule.is_active == True
    ).all()
    
    # Get approved reservations for this room and date
    reservations = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.date == date,
        Reservation.status == ReservationStatus.APPROVED
    ).all()
    
    # Combine schedules and reservations to get busy slots
    busy_slots = []
    
    for schedule in schedules:
        busy_slots.append({
            'start_time': schedule.start_time.strftime('%H:%M'),
            'end_time': schedule.end_time.strftime('%H:%M'),
            'type': 'schedule',
            'description': f"{schedule.subject} - {schedule.professor or 'N/A'}"
        })
    
    for reservation in reservations:
        busy_slots.append({
            'start_time': reservation.start_time.strftime('%H:%M'),
            'end_time': reservation.end_time.strftime('%H:%M'),
            'type': 'reservation',
            'description': reservation.purpose
        })
    
    # Sort by start time
    busy_slots.sort(key=lambda x: x['start_time'])
    
    # Generate available slots
    available_slots = []
    working_start = settings.working_hours_start.strftime('%H:%M')
    working_end = settings.working_hours_end.strftime('%H:%M')
    
    current_time = working_start
    
    for slot in busy_slots:
        if current_time < slot['start_time']:
            available_slots.append({
                'start_time': current_time,
                'end_time': slot['start_time']
            })
        current_time = slot['end_time']
    
    if current_time < working_end:
        available_slots.append({
            'start_time': current_time,
            'end_time': working_end
        })
    
    return jsonify({
        'room': room.to_dict(),
        'date': date_str,
        'busy_slots': busy_slots,
        'available_slots': available_slots,
        'working_hours': {
            'start': working_start,
            'end': working_end
        }
    }), 200

@student_bp.route('/reservations', methods=['POST'])
@jwt_required()
def create_reservation():
    """Create a new room reservation request"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != UserRole.STUDENT:
        return jsonify({'message': 'Acces interzis. Doar studenții pot face rezervări.'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['room_id', 'date', 'start_time', 'end_time', 'purpose']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'message': f'Câmpul {field} este obligatoriu'}), 400
    
    # Validate room
    room = Room.query.get(data.get('room_id'))
    if not room or not room.is_active:
        return jsonify({'message': 'Sala nu a fost găsită sau este inactivă'}), 404
    
    # Parse date and times
    try:
        date = datetime.strptime(data.get('date'), '%Y-%m-%d').date()
        start_time = datetime.strptime(data.get('start_time'), '%H:%M').time()
        end_time = datetime.strptime(data.get('end_time'), '%H:%M').time()
    except ValueError:
        return jsonify({'message': 'Format de dată sau oră invalid'}), 400
    
    # Validate date is in the future
    if date < datetime.now().date():
        return jsonify({'message': 'Data rezervării trebuie să fie în viitor'}), 400
    
    # Validate start time is before end time
    if start_time >= end_time:
        return jsonify({'message': 'Ora de început trebuie să fie înainte de ora de sfârșit'}), 400
    
    # Check if the room is available at the requested time
    is_available, conflict_message = check_room_availability(
        room_id=room.id,
        date=date,
        start_time=start_time,
        end_time=end_time
    )
    
    if not is_available:
        return jsonify({'message': f'Sala nu este disponibilă: {conflict_message}'}), 409
    
    # Create reservation
    reservation = Reservation(
        user_id=user.id,
        room_id=room.id,
        purpose=data.get('purpose'),
        date=date,
        start_time=start_time,
        end_time=end_time
    )
    
    db.session.add(reservation)
    db.session.commit()
    
    # Send notification to secretariat (async)
    send_reservation_notification(reservation)
    
    return jsonify({
        'message': 'Cererea de rezervare a fost trimisă cu succes',
        'reservation': reservation.to_dict()
    }), 201

@student_bp.route('/reservations', methods=['GET'])
@jwt_required()
def get_user_reservations():
    """Get all reservations for the current user"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'Utilizator negăsit'}), 404
    
    # Get query parameters
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build query
    query = Reservation.query.filter(Reservation.user_id == user.id)
    
    # Apply filters
    if status:
        try:
            status_enum = ReservationStatus(status)
            query = query.filter(Reservation.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status
    
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
    
    reservations = query.all()
    
    return jsonify({
        'reservations': [reservation.to_dict() for reservation in reservations]
    }), 200

@student_bp.route('/reservations/<int:reservation_id>', methods=['GET'])
@jwt_required()
def get_reservation_details(reservation_id):
    """Get details for a specific reservation"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'Utilizator negăsit'}), 404
    
    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({'message': 'Rezervare negăsită'}), 404
    
    # Check if the user owns this reservation or is admin/secretary
    if reservation.user_id != user.id and user.role == UserRole.STUDENT:
        return jsonify({'message': 'Acces interzis'}), 403
    
    return jsonify({
        'reservation': reservation.to_dict()
    }), 200

@student_bp.route('/reservations/<int:reservation_id>', methods=['DELETE'])
@jwt_required()
def cancel_reservation(reservation_id):
    """Cancel a pending reservation"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'Utilizator negăsit'}), 404
    
    reservation = Reservation.query.get(reservation_id)
    
    if not reservation:
        return jsonify({'message': 'Rezervare negăsită'}), 404
    
    # Check if the user owns this reservation
    if reservation.user_id != user.id:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Check if the reservation is still pending
    if reservation.status != ReservationStatus.PENDING:
        return jsonify({'message': 'Doar rezervările în așteptare pot fi anulate'}), 400
    
    # Delete the reservation
    db.session.delete(reservation)
    db.session.commit()
    
    return jsonify({
        'message': 'Rezervarea a fost anulată cu succes'
    }), 200
