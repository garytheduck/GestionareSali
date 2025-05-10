from app import create_app, db
from app.models.user import User, UserRole
from app.models.settings import InstitutionSettings
from app.models.room import Room
from app.models.schedule import Schedule, DayOfWeek
from app.models.reservation import Reservation, ReservationStatus
import os
from datetime import datetime, time, date, timedelta

def init_database_with_test_data():
    """Initialize the database with required tables and test data"""
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Add institution settings
        settings = InstitutionSettings.query.first()
        if not settings:
            settings = InstitutionSettings(
                name="Universitatea Ștefan cel Mare din Suceava",
                address="Strada Universității 13, Suceava 720229",
                current_semester="2024-2025-2"
            )
            db.session.add(settings)
        
        # Add users with different roles
        # Admin user
        admin = User.query.filter_by(email='admin@usv.ro').first()
        if not admin:
            admin = User(
                email='admin@usv.ro',
                first_name='Admin',
                last_name='USV',
                role=UserRole.ADMIN,
                password='admin123'
            )
            admin.google_id = 'admin_google_id_123'
            db.session.add(admin)
        
        # Secretary user
        secretary = User.query.filter_by(email='secretariat@usv.ro').first()
        if not secretary:
            secretary = User(
                email='secretariat@usv.ro',
                first_name='Secretar',
                last_name='Principal',
                role=UserRole.SECRETARY,
                password='secretary123',
                academic_title='Ing.'
            )
            secretary.google_id = 'secretary_google_id_123'
            db.session.add(secretary)
        
        # Student users (group leaders)
        student1 = User.query.filter_by(email='student1@student.usv.ro').first()
        if not student1:
            student1 = User(
                email='student1@student.usv.ro',
                first_name='Alexandru',
                last_name='Popescu',
                role=UserRole.STUDENT,
                password='student123'
            )
            student1.google_id = 'student1_google_id_123'
            db.session.add(student1)
        
        student2 = User.query.filter_by(email='student2@student.usv.ro').first()
        if not student2:
            student2 = User(
                email='student2@student.usv.ro',
                first_name='Maria',
                last_name='Ionescu',
                role=UserRole.STUDENT,
                password='student123'
            )
            student2.google_id = 'student2_google_id_123'
            db.session.add(student2)
        
        # Add rooms
        room1 = Room.query.filter_by(name='C201').first()
        if not room1:
            room1 = Room(
                name='C201',
                capacity=30,
                building='Corp C',
                floor=2,
                room_type='lecture',
                features='projector,whiteboard,computers'
            )
            db.session.add(room1)
        
        room2 = Room.query.filter_by(name='C301').first()
        if not room2:
            room2 = Room(
                name='C301',
                capacity=25,
                building='Corp C',
                floor=3,
                room_type='lab',
                features='projector,computers,specialized_equipment'
            )
            db.session.add(room2)
        
        room3 = Room.query.filter_by(name='A101').first()
        if not room3:
            room3 = Room(
                name='A101',
                capacity=100,
                building='Corp A',
                floor=1,
                room_type='lecture',
                features='projector,sound_system'
            )
            db.session.add(room3)
        
        # Commit changes to get IDs
        db.session.commit()
        
        # Add schedules for rooms
        # Get room IDs
        room1 = Room.query.filter_by(name='C201').first()
        room2 = Room.query.filter_by(name='C301').first()
        room3 = Room.query.filter_by(name='A101').first()
        
        # Check if schedules already exist
        if Schedule.query.count() == 0:
            # Schedule for room1
            schedule1 = Schedule(
                room_id=room1.id,
                day_of_week=DayOfWeek.MONDAY,
                start_time=time(8, 0),
                end_time=time(10, 0),
                subject='Programare Web',
                professor='Prof. Dr. Radu Prodan',
                group_name='A3',
                semester='2024-2025-2'
            )
            db.session.add(schedule1)
            
            schedule2 = Schedule(
                room_id=room1.id,
                day_of_week=DayOfWeek.TUESDAY,
                start_time=time(10, 0),
                end_time=time(12, 0),
                subject='Inteligență Artificială',
                professor='Conf. Dr. Mihai Dimian',
                group_name='A3',
                semester='2024-2025-2'
            )
            db.session.add(schedule2)
            
            # Schedule for room2
            schedule3 = Schedule(
                room_id=room2.id,
                day_of_week=DayOfWeek.WEDNESDAY,
                start_time=time(14, 0),
                end_time=time(16, 0),
                subject='Securitatea Sistemelor Informatice',
                professor='Lect. Dr. Ovidiu Gherman',
                group_name='A3',
                semester='2024-2025-2'
            )
            db.session.add(schedule3)
            
            schedule4 = Schedule(
                room_id=room2.id,
                day_of_week=DayOfWeek.THURSDAY,
                start_time=time(16, 0),
                end_time=time(18, 0),
                subject='Programare Paralelă și Distribuită',
                professor='Prof. Dr. Ștefan Gheorghe Pentiuc',
                group_name='A3',
                semester='2024-2025-2'
            )
            db.session.add(schedule4)
            
            # Schedule for room3
            schedule5 = Schedule(
                room_id=room3.id,
                day_of_week=DayOfWeek.FRIDAY,
                start_time=time(12, 0),
                end_time=time(14, 0),
                subject='Bazele Inteligenței Artificiale',
                professor='Prof. Dr. Adrian Graur',
                group_name='B2',
                semester='2024-2025-2'
            )
            db.session.add(schedule5)
        
        # Add reservations
        # Get user IDs
        student1 = User.query.filter_by(email='student1@student.usv.ro').first()
        
        # Check if reservations already exist
        if Reservation.query.count() == 0:
            # Current date for testing
            today = date.today()
            
            # Create a pending reservation
            reservation1 = Reservation(
                user_id=student1.id,
                room_id=room1.id,
                purpose='Examen Programare Web',
                date=today + timedelta(days=7),
                start_time=time(9, 0),
                end_time=time(11, 0)
            )
            db.session.add(reservation1)
            
            # Create an approved reservation
            reservation2 = Reservation(
                user_id=student1.id,
                room_id=room2.id,
                purpose='Examen Securitatea Sistemelor Informatice',
                date=today + timedelta(days=14),
                start_time=time(10, 0),
                end_time=time(12, 0)
            )
            # Approve the reservation
            reservation2.approve(admin.id)
            db.session.add(reservation2)
            
            # Create a rejected reservation
            reservation3 = Reservation(
                user_id=student1.id,
                room_id=room3.id,
                purpose='Examen Programare Paralelă și Distribuită',
                date=today + timedelta(days=10),
                start_time=time(14, 0),
                end_time=time(16, 0)
            )
            # Reject the reservation
            reservation3.reject(admin.id, 'Data propusă se suprapune cu alt examen. Vă rugăm să propuneți o altă dată.')
            db.session.add(reservation3)
        
        # Commit all changes
        db.session.commit()
        print("Database initialized with test data successfully!")

if __name__ == '__main__':
    init_database_with_test_data()
