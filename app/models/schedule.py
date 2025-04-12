from app import db
from datetime import datetime, time
import enum

class DayOfWeek(enum.Enum):
    MONDAY = 'monday'
    TUESDAY = 'tuesday'
    WEDNESDAY = 'wednesday'
    THURSDAY = 'thursday'
    FRIDAY = 'friday'
    SATURDAY = 'saturday'
    SUNDAY = 'sunday'

class Schedule(db.Model):
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    day_of_week = db.Column(db.Enum(DayOfWeek), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    professor = db.Column(db.String(255), nullable=True)
    group_name = db.Column(db.String(100), nullable=True)
    semester = db.Column(db.String(20), nullable=False)  # e.g., "2023-2024-1" for first semester
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, room_id, day_of_week, start_time, end_time, subject, 
                 professor=None, group_name=None, semester=None):
        self.room_id = room_id
        self.day_of_week = day_of_week
        self.start_time = start_time
        self.end_time = end_time
        self.subject = subject
        self.professor = professor
        self.group_name = group_name
        self.semester = semester
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'room_name': self.room.name if self.room else None,
            'day_of_week': self.day_of_week.value,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'subject': self.subject,
            'professor': self.professor,
            'group_name': self.group_name,
            'semester': self.semester,
            'is_active': self.is_active,
        }
    
    def __repr__(self):
        return f"<Schedule {self.subject} - {self.day_of_week.value} {self.start_time}-{self.end_time}>"
