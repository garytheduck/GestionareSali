from app import db
from datetime import datetime
import enum
import uuid

class ReservationStatus(enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    purpose = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.Enum(ReservationStatus), default=ReservationStatus.PENDING, nullable=False)
    rejection_reason = db.Column(db.String(255), nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_reservations')
    
    def __init__(self, user_id, room_id, purpose, date, start_time, end_time):
        self.user_id = user_id
        self.room_id = room_id
        self.purpose = purpose
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        # Generate a unique reference number: RZV.XX-DD.MM.YYYY
        today = datetime.now()
        random_part = str(uuid.uuid4())[:2].upper()
        self.reference_number = f"RZV.{random_part}-{today.day:02d}.{today.month:02d}.{today.year}"
    
    def approve(self, reviewer_id):
        self.status = ReservationStatus.APPROVED
        self.reviewed_by = reviewer_id
        self.reviewed_at = datetime.utcnow()
    
    def reject(self, reviewer_id, reason):
        self.status = ReservationStatus.REJECTED
        self.reviewed_by = reviewer_id
        self.rejection_reason = reason
        self.reviewed_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'reference_number': self.reference_number,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else None,
            'user_email': self.user.email if self.user else None,
            'room_id': self.room_id,
            'room_name': self.room.name if self.room else None,
            'purpose': self.purpose,
            'date': self.date.strftime('%Y-%m-%d'),
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'status': self.status.value,
            'rejection_reason': self.rejection_reason,
            'reviewed_by': self.reviewer.full_name if self.reviewer else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_at': self.created_at.isoformat(),
        }
    
    def __repr__(self):
        return f"<Reservation {self.reference_number} - {self.status.value}>"
