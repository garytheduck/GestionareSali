from flask import Blueprint, request, jsonify, redirect, url_for, session
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    jwt_required, get_jwt_identity
)
from app.models.user import User, UserRole
from app import db
from app.utils.google_auth import create_flow, get_google_user_info, get_or_create_user
import datetime
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Check if this is a Google login
    if data and data.get('googleToken'):
        # Process Google token
        user_info = get_google_user_info(data.get('googleToken'))
        
        if not user_info:
            return jsonify({'message': 'Token Google invalid'}), 401
        
        # Extract email domain for error message
        email = user_info.get('email', '')
        email_domain = email.split('@')[-1].lower() if '@' in email else ''
        
        # Get or create user from Google info
        user = get_or_create_user(user_info)
        
        # Check if user was created (will be None if domain not allowed)
        if not user:
            return jsonify({
                'message': 'Autentificare eșuată. Doar adresele de email de la domeniile student.usv.ro și usm.ro sunt acceptate.',
                'error': 'unauthorized_domain',
                'domain': email_domain
            }), 403
        
        if not user.is_active:
            return jsonify({'message': 'Contul este dezactivat. Contactați administratorul.'}), 403
        
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            'message': 'Autentificare Google reușită',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
    
    # Regular email/password login
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

@auth_bp.route('/google-login', methods=['GET'])
def google_login():
    """Initiate Google OAuth flow"""
    # Create the flow using the create_flow helper
    flow = create_flow()
    
    # Generate the authorization URL
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Store the state in the session
    session['state'] = state
    
    # Redirect to Google's OAuth page
    return redirect(authorization_url)

@auth_bp.route('/callback', methods=['GET'])
def callback():
    """Handle Google OAuth callback"""
    # Get the state from the session
    state = session.get('state')
    
    # Create the flow using the create_flow helper
    flow = create_flow()
    
    # Use the authorization server's response to fetch the OAuth 2.0 tokens
    flow.fetch_token(authorization_response=request.url)
    
    # Get user info from the ID token
    credentials = flow.credentials
    user_info = get_google_user_info(credentials.id_token)
    
    if not user_info:
        return jsonify({'message': 'Autentificare Google eșuată'}), 401
    
    # Get or create user
    user = get_or_create_user(user_info)
    
    if not user.is_active:
        return jsonify({'message': 'Contul este dezactivat. Contactați administratorul.'}), 403
    
    # Create tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    # Redirect to frontend with tokens
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    redirect_url = f"{frontend_url}/auth-callback?access_token={access_token}&refresh_token={refresh_token}"
    
    return redirect(redirect_url)
