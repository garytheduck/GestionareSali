from app import db
from datetime import datetime

class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    building = db.Column(db.String(100), nullable=False)
    floor = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)  # lecture, lab, seminar, etc.
    features = db.Column(db.String(255), nullable=True)  # e.g., "projector,whiteboard,computers"
    usv_id = db.Column(db.String(50), nullable=True, unique=True)  # ID from USV API
    description = db.Column(db.String(255), nullable=True)  # Additional details from USV API
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    schedules = db.relationship('Schedule', backref='room', lazy='dynamic')
    reservations = db.relationship('Reservation', backref='room', lazy='dynamic')
    
    def __init__(self, name, capacity, building, floor, room_type, features=None):
        self.name = name
        self.capacity = capacity
        self.building = building
        self.floor = floor
        self.room_type = room_type
        self.features = features
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'building': self.building,
            'floor': self.floor,
            'room_type': self.room_type,
            'features': self.features.split(',') if self.features else [],
            'usv_id': self.usv_id,
            'description': self.description,
            'is_active': self.is_active,
        }
    
    def __repr__(self):
        return f"<Room {self.name}>"
