"""
Model pentru examen/programare examene
"""
from app import db
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship

class Exam(db.Model):
    """
    Model pentru examen/programare a unui examen
    """
    __tablename__ = 'exams'
    
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    
    # Informații despre programare
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    exam_type = Column(String(50), nullable=False)  # Examen, colocviu, restanță, etc.
    semester = Column(String(20), nullable=False)  # Semestrul 1 sau 2
    academic_year = Column(String(20), nullable=False)  # Ex: 2023-2024
    
    # Informații suplimentare
    max_students = Column(Integer, nullable=True)  # Capacitatea maximă de studenți
    notes = Column(Text, nullable=True)  # Note sau observații
    is_active = Column(Boolean, default=True)  # Flag pentru a marca ștergerea soft
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relații
    course = relationship("Course", back_populates="exams")
    room = relationship("Room", backref="exams")
    registrations = relationship("ExamRegistration", back_populates="exam", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Exam {self.id}: {self.course.name} - {self.start_time}>"


class ExamRegistration(db.Model):
    """
    Model pentru înregistrarea studenților la examen
    """
    __tablename__ = 'exam_registrations'
    
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('exams.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Status înregistrare
    status = Column(String(20), default='registered')  # registered, confirmed, cancelled, attended, etc.
    registration_time = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relații
    exam = relationship("Exam", back_populates="registrations")
    student = relationship("User")
    
    def __repr__(self):
        return f"<ExamRegistration {self.id}: {self.student.email} - {self.exam_id}>"
