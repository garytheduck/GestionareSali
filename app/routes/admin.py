from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, time
from app.models.user import User, UserRole
from app.models.settings import InstitutionSettings
from app.models.room import Room
from app.models.schedule import Schedule, DayOfWeek
from app.models.reservation import Reservation
from app import db
from app.utils.schedule_importer import import_schedule_from_excel, import_schedule_from_usv_api
import pandas as pd
import io

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_settings():
    """Get institution settings"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    settings = InstitutionSettings.get_settings()
    
    return jsonify({
        'settings': settings.to_dict()
    }), 200

@admin_bp.route('/settings', methods=['PUT'])
@jwt_required()
def update_settings():
    """Update institution settings"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    data = request.get_json()
    settings = InstitutionSettings.get_settings()
    
    # Update fields
    if data.get('name'):
        settings.name = data.get('name')
    
    if data.get('address'):
        settings.address = data.get('address')
    
    if data.get('working_hours_start'):
        try:
            working_hours_start = datetime.strptime(data.get('working_hours_start'), '%H:%M').time()
            settings.working_hours_start = working_hours_start
        except ValueError:
            return jsonify({'message': 'Format oră invalid pentru working_hours_start'}), 400
    
    if data.get('working_hours_end'):
        try:
            working_hours_end = datetime.strptime(data.get('working_hours_end'), '%H:%M').time()
            settings.working_hours_end = working_hours_end
        except ValueError:
            return jsonify({'message': 'Format oră invalid pentru working_hours_end'}), 400
    
    if data.get('daily_report_time'):
        try:
            daily_report_time = datetime.strptime(data.get('daily_report_time'), '%H:%M').time()
            settings.daily_report_time = daily_report_time
        except ValueError:
            return jsonify({'message': 'Format oră invalid pentru daily_report_time'}), 400
    
    if data.get('logo_url'):
        settings.logo_url = data.get('logo_url')
    
    if data.get('current_semester'):
        settings.current_semester = data.get('current_semester')
    
    db.session.commit()
    
    return jsonify({
        'message': 'Setările au fost actualizate cu succes',
        'settings': settings.to_dict()
    }), 200

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """Get all users with optional role filter"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Get query parameters
    role = request.args.get('role')
    
    # Build query
    query = User.query
    
    # Apply filters
    if role:
        try:
            role_enum = UserRole(role)
            query = query.filter(User.role == role_enum)
        except ValueError:
            pass  # Ignore invalid role
    
    users = query.all()
    
    return jsonify({
        'users': [user.to_dict() for user in users]
    }), 200

@admin_bp.route('/users', methods=['POST'])
@jwt_required()
def create_user():
    """Create a new user (secretary or admin)"""
    current_user_id = get_jwt_identity()
    admin = User.query.get(current_user_id)
    
    if not admin or admin.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['email', 'password', 'first_name', 'last_name', 'role']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'message': f'Câmpul {field} este obligatoriu'}), 400
    
    # Check if email already exists
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'message': 'Adresa de email este deja înregistrată'}), 409
    
    # Validate role
    role_str = data.get('role')
    try:
        role = UserRole(role_str)
        # Students should register themselves, not be created by admin
        if role == UserRole.STUDENT:
            return jsonify({'message': 'Administratorii nu pot crea conturi de student'}), 400
    except ValueError:
        return jsonify({'message': 'Rol invalid'}), 400
    
    # Create new user
    new_user = User(
        email=data.get('email'),
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        password=data.get('password'),
        role=role,
        academic_title=data.get('academic_title')
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'message': 'Utilizator creat cu succes',
        'user': new_user.to_dict()
    }), 201

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """Update user details"""
    current_user_id = get_jwt_identity()
    admin = User.query.get(current_user_id)
    
    if not admin or admin.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'Utilizator negăsit'}), 404
    
    data = request.get_json()
    
    # Update fields
    if data.get('first_name'):
        user.first_name = data.get('first_name')
    
    if data.get('last_name'):
        user.last_name = data.get('last_name')
    
    if data.get('email'):
        # Check if email is already used by another user
        existing_user = User.query.filter_by(email=data.get('email')).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'message': 'Adresa de email este deja utilizată'}), 409
        user.email = data.get('email')
    
    if data.get('academic_title'):
        user.academic_title = data.get('academic_title')
    
    if data.get('is_active') is not None:
        user.is_active = data.get('is_active')
    
    if data.get('password'):
        user.set_password(data.get('password'))
    
    db.session.commit()
    
    return jsonify({
        'message': 'Utilizator actualizat cu succes',
        'user': user.to_dict()
    }), 200

@admin_bp.route('/rooms', methods=['POST'])
@jwt_required()
def create_room():
    """Create a new room"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'capacity', 'building', 'floor', 'room_type']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'message': f'Câmpul {field} este obligatoriu'}), 400
    
    # Check if room name already exists
    if Room.query.filter_by(name=data.get('name')).first():
        return jsonify({'message': 'O sală cu acest nume există deja'}), 409
    
    # Create new room
    new_room = Room(
        name=data.get('name'),
        capacity=data.get('capacity'),
        building=data.get('building'),
        floor=data.get('floor'),
        room_type=data.get('room_type'),
        features=data.get('features')
    )
    
    db.session.add(new_room)
    db.session.commit()
    
    return jsonify({
        'message': 'Sala a fost creată cu succes',
        'room': new_room.to_dict()
    }), 201

@admin_bp.route('/rooms/<int:room_id>', methods=['PUT'])
@jwt_required()
def update_room(room_id):
    """Update room details"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    room = Room.query.get(room_id)
    
    if not room:
        return jsonify({'message': 'Sala nu a fost găsită'}), 404
    
    data = request.get_json()
    
    # Update fields
    if data.get('name'):
        # Check if name is already used by another room
        existing_room = Room.query.filter_by(name=data.get('name')).first()
        if existing_room and existing_room.id != room.id:
            return jsonify({'message': 'O sală cu acest nume există deja'}), 409
        room.name = data.get('name')
    
    if data.get('capacity'):
        room.capacity = data.get('capacity')
    
    if data.get('building'):
        room.building = data.get('building')
    
    if data.get('floor'):
        room.floor = data.get('floor')
    
    if data.get('room_type'):
        room.room_type = data.get('room_type')
    
    if data.get('features'):
        room.features = data.get('features')
    
    if data.get('is_active') is not None:
        room.is_active = data.get('is_active')
    
    db.session.commit()
    
    return jsonify({
        'message': 'Sala a fost actualizată cu succes',
        'room': room.to_dict()
    }), 200

@admin_bp.route('/schedule/import', methods=['POST'])
@jwt_required()
def import_schedule():
    """Import schedule from Excel file"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'message': 'Niciun fișier nu a fost încărcat'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'message': 'Niciun fișier selectat'}), 400
    
    # Check file extension
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        return jsonify({'message': 'Format de fișier invalid. Sunt acceptate doar fișiere Excel (.xlsx, .xls) sau CSV (.csv)'}), 400
    
    # Get semester parameter
    semester = request.form.get('semester')
    if not semester:
        return jsonify({'message': 'Parametrul semester este obligatoriu'}), 400
    
    # Read file content
    file_content = file.read()
    file_io = io.BytesIO(file_content)
    
    try:
        # Process the file and import schedule
        result = import_schedule_from_excel(file_io, file.filename, semester)
        
        return jsonify({
            'message': 'Orarul a fost importat cu succes',
            'stats': result
        }), 200
    except Exception as e:
        return jsonify({'message': f'Eroare la importul orarului: {str(e)}'}), 400

@admin_bp.route('/schedule/import-usv', methods=['POST'])
@jwt_required()
def import_schedule_from_usv():
    """Import schedule from USV API"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    data = request.get_json()
    
    # Get semester parameter
    semester = data.get('semester')
    if not semester:
        return jsonify({'message': 'Parametrul semester este obligatoriu'}), 400
    
    try:
        # Process the USV API data and import schedule
        result = import_schedule_from_usv_api(semester)
        
        return jsonify({
            'message': 'Orarul a fost importat cu succes din API-ul USV',
            'stats': result
        }), 200
    except Exception as e:
        return jsonify({'message': f'Eroare la importul orarului din API-ul USV: {str(e)}'}), 400

@admin_bp.route('/reset-semester', methods=['POST'])
@jwt_required()
def reset_semester():
    """Reset reservations for a new semester"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role != UserRole.ADMIN:
        return jsonify({'message': 'Acces interzis'}), 403
    
    data = request.get_json()
    
    # Validate new semester
    if not data or not data.get('new_semester'):
        return jsonify({'message': 'Parametrul new_semester este obligatoriu'}), 400
    
    new_semester = data.get('new_semester')
    
    # Update institution settings with new semester
    settings = InstitutionSettings.get_settings()
    settings.current_semester = new_semester
    
    # Archive or delete old reservations
    if data.get('delete_reservations', False):
        # Delete all reservations
        Reservation.query.delete()
    else:
        # Mark all schedules as inactive
        Schedule.query.update({Schedule.is_active: False})
    
    db.session.commit()
    
    return jsonify({
        'message': 'Semestrul a fost resetat cu succes',
        'new_semester': new_semester
    }), 200
