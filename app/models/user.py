from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum

class UserRole(enum.Enum):
    STUDENT = 'student'
    SECRETARY = 'secretary'
    ADMIN = 'admin'

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional fields based on role
    academic_title = db.Column(db.String(100), nullable=True)  # For professors/secretaries
    
    # Relationships
    reservations = db.relationship('Reservation', foreign_keys='Reservation.user_id', backref='user', lazy='dynamic')
    
    def __init__(self, email, first_name, last_name, role, password=None, academic_title=None):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.academic_title = academic_title
        if password:
            self.set_password(password)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'role': self.role.value,
            'academic_title': self.academic_title,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"
