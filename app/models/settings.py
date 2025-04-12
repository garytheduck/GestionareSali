from app import db
from datetime import datetime, time

class InstitutionSettings(db.Model):
    __tablename__ = 'institution_settings'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    working_hours_start = db.Column(db.Time, default=time(8, 0), nullable=False)  # 8:00 AM
    working_hours_end = db.Column(db.Time, default=time(20, 0), nullable=False)  # 8:00 PM
    daily_report_time = db.Column(db.Time, default=time(16, 0), nullable=False)  # 4:00 PM
    logo_url = db.Column(db.String(255), nullable=True)
    current_semester = db.Column(db.String(20), nullable=False)  # e.g., "2023-2024-1"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, name, address, current_semester, working_hours_start=None, 
                 working_hours_end=None, daily_report_time=None, logo_url=None):
        self.name = name
        self.address = address
        self.current_semester = current_semester
        if working_hours_start:
            self.working_hours_start = working_hours_start
        if working_hours_end:
            self.working_hours_end = working_hours_end
        if daily_report_time:
            self.daily_report_time = daily_report_time
        self.logo_url = logo_url
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'working_hours_start': self.working_hours_start.strftime('%H:%M'),
            'working_hours_end': self.working_hours_end.strftime('%H:%M'),
            'daily_report_time': self.daily_report_time.strftime('%H:%M'),
            'logo_url': self.logo_url,
            'current_semester': self.current_semester,
            'updated_at': self.updated_at.isoformat(),
        }
    
    @classmethod
    def get_settings(cls):
        """Get the institution settings or create default if not exists"""
        settings = cls.query.first()
        if not settings:
            settings = cls(
                name="Universitatea de Științe Aplicate",
                address="Strada Exemplu, Nr. 123, Oraș, Țară",
                current_semester="2023-2024-1"
            )
            db.session.add(settings)
            db.session.commit()
        return settings
    
    def __repr__(self):
        return f"<InstitutionSettings {self.name}>"
