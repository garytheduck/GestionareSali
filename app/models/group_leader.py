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
