from flask import current_app, url_for, request, redirect, session
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport import requests
import os
import json
import pathlib

from app.models.user import User, UserRole
from app import db

# Configuration for Google OAuth
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

def create_flow():
    """Create a Google OAuth flow object"""
    # Create a flow instance to manage the OAuth 2.0 Authorization Grant Flow steps
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [url_for("auth.callback", _external=True)],
            }
        },
        scopes=["openid", "email", "profile"],
    )
    return flow

def get_google_user_info(token, test_email=None, test_role=None):
    """Verify Google ID token and extract user info"""
    try:
        # Verifică dacă este token-ul de test pentru testare automată
        if token == 'test_token_for_automated_testing':
            # Obținem datele din request dacă sunt disponibile
            from flask import request
            
            try:
                request_data = request.get_json() if request and request.is_json else {}
            except Exception as e:
                current_app.logger.error(f"Error parsing JSON from request: {str(e)}")
                request_data = {}
            
            # Log pentru depanare
            current_app.logger.info(f"Test login data: {request_data}")
            
            # Folosim email-ul și rolul trimise de frontend dacă sunt disponibile
            test_email = test_email or request_data.get('testEmail') or 'test.user@usm.ro'
            test_role = test_role or request_data.get('testRole') or 'student'
            
            # Generăm numele bazat pe email
            try:
                name_parts = test_email.split('@')[0].split('.')
                first_name = name_parts[0].capitalize() if len(name_parts) > 0 else 'Test'
                last_name = name_parts[1].capitalize() if len(name_parts) > 1 else 'User'
                full_name = f"{first_name} {last_name}"
            except Exception as e:
                current_app.logger.error(f"Error parsing name from email: {str(e)}")
                first_name = 'Test'
                last_name = 'User'
                full_name = 'Test User'
            
            # Returnează informații de test pentru utilizator
            return {
                'email': test_email,  # Folosim email-ul specificat
                'name': full_name,
                'given_name': first_name,
                'family_name': last_name,
                'picture': f'https://ui-avatars.com/api/?name={first_name}+{last_name}&background=random',
                'google_id': f'test_user_id_{test_email}',  # ID unic bazat pe email
                'is_test_user': True,  # Marcăm utilizatorul ca fiind de test
                'test_role': test_role  # Salvăm rolul specificat
            }
    except Exception as e:
        current_app.logger.error(f"Error in get_google_user_info for test token: {str(e)}")
        # Returnează un utilizator de test implicit în caz de eroare
        return {
            'email': 'test.fallback@usv.ro',
            'name': 'Test Fallback',
            'given_name': 'Test',
            'family_name': 'Fallback',
            'picture': 'https://ui-avatars.com/api/?name=Test+Fallback&background=random',
            'google_id': 'test_user_id_fallback',
            'is_test_user': True,
            'test_role': 'student'
        }
    
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), GOOGLE_CLIENT_ID
        )
        
        # Check if the token is issued by Google
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Wrong issuer.')
            
        # Return user info
        return {
            'email': idinfo['email'],
            'name': idinfo.get('name', ''),
            'given_name': idinfo.get('given_name', ''),
            'family_name': idinfo.get('family_name', ''),
            'picture': idinfo.get('picture', ''),
            'google_id': idinfo.get('sub', ''),  # 'sub' is the Google user ID
            'is_test_user': False
        }
    except Exception as e:
        current_app.logger.error(f"Error verifying Google token: {str(e)}")
        return None

def get_or_create_user(user_info):
    """Get existing user or create a new one based on Google user info"""
    try:
        # Verificăm dacă avem informațiile necesare
        if not user_info or not isinstance(user_info, dict):
            current_app.logger.error(f"Invalid user_info: {user_info}")
            return None
            
        email = user_info.get('email')
        if not email:
            current_app.logger.error("No email provided in user_info")
            return None
            
        google_id = user_info.get('google_id')
        is_test_user = user_info.get('is_test_user', False)
        
        # Dacă este un utilizator de test, folosim email-ul și rolul trimise de frontend
        if is_test_user:
            # Email-ul este deja setat în get_google_user_info
            # Determinăm rolul în funcție de email sau de rolul specificat
            test_role = user_info.get('test_role', 'student')
            
            # Log pentru depanare
            current_app.logger.info(f"Processing test user: {email}, role: {test_role}")
            
            # Folosim explicit rolul trimis de frontend dacă este disponibil
            if test_role and test_role != 'student':
                if test_role == 'secretary':
                    role_override = UserRole.SECRETARY
                elif test_role == 'admin':
                    role_override = UserRole.ADMIN
                elif test_role == 'teacher':
                    role_override = UserRole.TEACHER
                else:
                    role_override = UserRole.STUDENT
            # Altfel, determinăm rolul în funcție de adresa de email
            else:
                if '@student.' in email:
                    role_override = UserRole.STUDENT
                elif '@secretary.' in email or 'secretary' in email:
                    role_override = UserRole.SECRETARY
                elif 'admin' in email:
                    role_override = UserRole.ADMIN
                elif '@usv.ro' in email or '@usm.ro' in email:
                    role_override = UserRole.TEACHER
                else:
                    # Default la student dacă nu putem determina rolul
                    role_override = UserRole.STUDENT
            
            # Logging pentru depanare
            current_app.logger.info(f"Test role from frontend: {test_role}")
            current_app.logger.info(f"Email domain: {email.split('@')[-1] if '@' in email else 'no domain'}")
            current_app.logger.info(f"Email contains 'secretary': {'secretary' in email}")
            current_app.logger.info(f"Email contains 'admin': {'admin' in email}")
            current_app.logger.info(f"Final role_override: {role_override}")
                
            current_app.logger.info(f"Test user login with email: {email}, role: {role_override}")
            
            # Email-ul este deja setat în get_google_user_info, nu trebuie suprascris
    except Exception as e:
        current_app.logger.error(f"Error in get_or_create_user initial processing: {str(e)}")
        # Setarea valorilor implicite în caz de eroare
        email = user_info.get('email', 'test.fallback@usv.ro')
        google_id = user_info.get('google_id', 'test_user_id_fallback')
        is_test_user = True
        role_override = UserRole.STUDENT
    
    try:
        # Check if email domain is allowed (student.usv.ro or usm.ro)
        email_domain = email.split('@')[-1].lower() if '@' in email else ''
        
        # Pentru utilizatorii de test, permitem orice domeniu de email
        if not is_test_user and email_domain not in ['student.usv.ro', 'usm.ro', 'usv.ro']:
            # Return None for unauthorized domains
            current_app.logger.warning(f"Unauthorized email domain: {email_domain}")
            return None
        
        # First try to find user by Google ID if available
        user = None
        if google_id:
            try:
                user = User.query.filter_by(google_id=google_id).first()
            except Exception as e:
                current_app.logger.error(f"Error finding user by google_id: {str(e)}")
        
        # If not found by Google ID, try by email
        if not user:
            try:
                user = User.query.filter_by(email=email).first()
            except Exception as e:
                current_app.logger.error(f"Error finding user by email: {str(e)}")
        
        if user:
            # User exists, update Google-specific fields if needed
            try:
                if not user.google_id and google_id:
                    user.google_id = google_id
                if not user.profile_picture and user_info.get('picture'):
                    user.profile_picture = user_info.get('picture')
                if user.auth_provider == 'local':
                    user.auth_provider = 'google'
                
                db.session.commit()
                current_app.logger.info(f"Updated existing user: {email}, role: {user.role}")
                return user
            except Exception as e:
                current_app.logger.error(f"Error updating existing user: {str(e)}")
                db.session.rollback()
        
        # Determine role based on email domain or override for test users
        if is_test_user:
            role = role_override
            current_app.logger.info(f"Using role_override for test user: {role}")
        elif email_domain == 'student.usv.ro':
            role = UserRole.STUDENT  # Student role for student.usv.ro emails
        elif email_domain in ['usm.ro', 'usv.ro']:
            # Verificăm dacă email-ul conține cuvinte cheie pentru a determina rolul
            if 'admin' in email:
                role = UserRole.ADMIN
            elif 'secretary' in email:
                role = UserRole.SECRETARY
            else:
                role = UserRole.TEACHER  # Default pentru domeniul usv.ro/usm.ro
        else:
            # Aceasta nu ar trebui să se întâmple din cauza verificării domeniului de mai sus
            current_app.logger.error(f"Unexpected email domain passed validation: {email_domain}")
            if is_test_user:
                # Pentru utilizatorii de test, folosim rolul implicit
                role = role_override
            else:
                return None
        
        # Create new user
        try:
            new_user = User(
                email=email,
                first_name=user_info.get('given_name', ''),
                last_name=user_info.get('family_name', ''),
                role=role,
                google_id=google_id,
                profile_picture=user_info.get('picture'),
                auth_provider='google'
            )
            
            db.session.add(new_user)
            db.session.commit()
            current_app.logger.info(f"Created new user: {email}, role: {role}")
            
            return new_user
        except Exception as e:
            current_app.logger.error(f"Error creating new user: {str(e)}")
            db.session.rollback()
            
            # În caz de eroare la crearea utilizatorului, încercăm să găsim utilizatorul din nou
            # (poate a fost creat între timp)
            try:
                user = User.query.filter_by(email=email).first()
                if user:
                    return user
            except Exception as search_error:
                current_app.logger.error(f"Error finding user after creation failure: {str(search_error)}")
            
            return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error in get_or_create_user: {str(e)}")
        return None
