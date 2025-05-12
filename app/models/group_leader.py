"""
Model pentru șefii de grupă
"""
from datetime import datetime
from app import db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

class GroupLeader(db.Model):
    """Model care reprezintă un șef de grupă"""
    __tablename__ = 'group_leaders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='group_leader_info')
    
    # Informații despre grupă
    group_name = db.Column(db.String(50), nullable=False)  # Ex: 3211A
    faculty = db.Column(db.String(100), nullable=False)    # Facultatea
    study_program = db.Column(db.String(100), nullable=False)  # Programul de studiu (ex: Calculatoare)
    year_of_study = db.Column(db.Integer, nullable=False)  # Anul de studiu (1-4)
    
    # Semestrul curent
    current_semester = db.Column(db.String(20), nullable=False)  # Ex: "1", "2"
    academic_year = db.Column(db.String(20), nullable=False)  # Ex: "2024-2025"
    
    # Câmpuri de audit
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<GroupLeader: {self.user.first_name} {self.user.last_name} ({self.group_name})>"
        
    def to_dict(self):
        """Convert the model to a dictionary for serialization"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.user.email if self.user else None,
            'first_name': self.user.first_name if self.user else None,
            'last_name': self.user.last_name if self.user else None,
            'group_name': self.group_name,
            'faculty': self.faculty,
            'study_program': self.study_program,
            'year_of_study': self.year_of_study,
            'current_semester': self.current_semester,
            'academic_year': self.academic_year,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # Include user data in a nested object for backward compatibility
            'user': {
                'first_name': self.user.first_name if self.user else None,
                'last_name': self.user.last_name if self.user else None,
                'email': self.user.email if self.user else None
            }
        }
        return data
