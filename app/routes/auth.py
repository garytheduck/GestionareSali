from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    jwt_required, get_jwt_identity
)
from app.models.user import User, UserRole
from app import db
import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Email și parola sunt obligatorii'}), 400
    
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user or not user.check_password(data.get('password')):
        return jsonify({'message': 'Email sau parolă incorectă'}), 401
    
    if not user.is_active:
        return jsonify({'message': 'Contul este dezactivat. Contactați administratorul.'}), 403
    
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        'message': 'Autentificare reușită',
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'message': f'Câmpul {field} este obligatoriu'}), 400
    
    # Check if email already exists
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'message': 'Adresa de email este deja înregistrată'}), 409
    
    # Validate email domain for students
    email = data.get('email')
    if '@student.' in email:
        role = UserRole.STUDENT
    else:
        # For non-student emails, default to student but allow override if specified
        role_str = data.get('role', 'student')
        try:
            role = UserRole(role_str)
        except ValueError:
            return jsonify({'message': 'Rol invalid'}), 400
    
    # Create new user
    new_user = User(
        email=email,
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        password=data.get('password'),
        role=role,
        academic_title=data.get('academic_title')
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'message': 'Înregistrare reușită',
        'user': new_user.to_dict()
    }), 201

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return jsonify({'message': 'Utilizator invalid sau inactiv'}), 401
    
    access_token = create_access_token(identity=current_user_id)
    
    return jsonify({
        'access_token': access_token
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_user_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'Utilizator negăsit'}), 404
    
    return jsonify({
        'user': user.to_dict()
    }), 200

@auth_bp.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'Utilizator negăsit'}), 404
    
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'message': 'Parola curentă și parola nouă sunt obligatorii'}), 400
    
    if not user.check_password(data.get('current_password')):
        return jsonify({'message': 'Parola curentă este incorectă'}), 401
    
    user.set_password(data.get('new_password'))
    db.session.commit()
    
    return jsonify({
        'message': 'Parola a fost schimbată cu succes'
    }), 200
