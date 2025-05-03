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

def get_google_user_info(token):
    """Verify Google ID token and extract user info"""
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
            'google_id': idinfo.get('sub', '')  # 'sub' is the Google user ID
        }
    except Exception as e:
        current_app.logger.error(f"Error verifying Google token: {str(e)}")
        return None

def get_or_create_user(user_info):
    """Get existing user or create a new one based on Google user info"""
    email = user_info['email']
    google_id = user_info.get('google_id')
    
    # First try to find user by Google ID if available
    user = None
    if google_id:
        user = User.query.filter_by(google_id=google_id).first()
    
    # If not found by Google ID, try by email
    if not user:
        user = User.query.filter_by(email=email).first()
    
    if user:
        # User exists, update Google-specific fields if needed
        if not user.google_id and google_id:
            user.google_id = google_id
        if not user.profile_picture and user_info.get('picture'):
            user.profile_picture = user_info.get('picture')
        if user.auth_provider == 'local':
            user.auth_provider = 'google'
        
        db.session.commit()
        return user
    
    # Determine role based on email domain
    if '@student.' in email:
        role = UserRole.STUDENT
    else:
        # Default to student for other emails
        role = UserRole.STUDENT
    
    # Create new user
    new_user = User(
        email=email,
        first_name=user_info.get('given_name', ''),
        last_name=user_info.get('family_name', ''),
        role=role,
        google_id=google_id,
        profile_picture=user_info.get('picture'),
        auth_provider='google'
        # No password for Google Auth users
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return new_user
