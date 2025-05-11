"""
Model pentru disciplinele de studiu
"""
from datetime import datetime
from app import db
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

class ExamType(enum.Enum):
    EXAM = 'exam'
    COLLOQUIUM = 'colloquium'
    PROJECT = 'project'

class Course(db.Model):
    """Model care reprezintă o disciplină (curs) din planul de învățământ"""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)  # Codul disciplinei
    name = db.Column(db.String(255), nullable=False)  # Denumirea disciplinei
    faculty = db.Column(db.String(100), nullable=False)  # Facultatea
    department = db.Column(db.String(100), nullable=True)  # Departamentul
    study_program = db.Column(db.String(100), nullable=False)  # Programul de studiu (ex: Calculatoare)
    year_of_study = db.Column(db.Integer, nullable=False)  # Anul de studiu (1-4)
    semester = db.Column(db.String(20), nullable=False)  # Semestrul (ex: "1", "2")
    credits = db.Column(db.Integer, nullable=True)  # Numărul de credite
    group_name = db.Column(db.String(50), nullable=False)  # Numele grupei (ex: 3211A)
    exam_type = db.Column(db.Enum(ExamType), nullable=False, default=ExamType.EXAM)  # Tipul de evaluare
    
    # Relație cu utilizatorii (profesorii)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref='taught_courses')
    
    # Asistent (poate fi null)
    assistant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assistant = db.relationship('User', foreign_keys=[assistant_id], backref='assisted_courses')
    
    # Detalii despre planificarea examenului
    proposed_date = db.Column(db.DateTime, nullable=True)  # Data propusă de șeful de grupă
    approved_date = db.Column(db.DateTime, nullable=True)  # Data aprobată de profesor
    exam_room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    exam_room = db.relationship('Room', backref='courses_with_exams')
    exam_duration = db.Column(db.Integer, nullable=True)  # Durata în ore
    
    # Relație cu examenele
    exams = db.relationship('Exam', back_populates='course', cascade='all, delete-orphan')
    
    # Status examen
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    rejection_reason = db.Column(db.String(255), nullable=True)
    
    # Câmpuri de audit
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Course {self.code}: {self.name} ({self.group_name})>"
