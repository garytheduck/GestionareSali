from app import create_app, db
from app.models.user import User, UserRole
from app.models.room import Room
from app.models.reservation import Reservation, ReservationStatus
from app.models.schedule import Schedule, DayOfWeek
from datetime import datetime, time, date, timedelta
import random

app = create_app()

def populate_users():
    """Populate database with sample users for each role"""
    print("Populating users...")
    
    # Admin user
    admin = User(
        email="admin@usv.ro",
        first_name="Admin",
        last_name="USV",
        role=UserRole.ADMIN,
        password="admin123",
        auth_provider="local"
    )
    
    # Secretary users
    secretary1 = User(
        email="secretary1@usm.ro",
        first_name="Maria",
        last_name="Popescu",
        role=UserRole.SECRETARY,
        password="secretary123",
        academic_title="Ing.",
        auth_provider="local"
    )
    
    secretary2 = User(
        email="secretary2@usm.ro",
        first_name="Ion",
        last_name="Ionescu",
        role=UserRole.SECRETARY,
        password="secretary123",
        academic_title="Dr.",
        auth_provider="local"
    )
    
    # Teacher users
    teachers = [
        User(
            email="teacher1@usv.ro",
            first_name="Alexandru",
            last_name="Popescu",
            role=UserRole.SECRETARY,  # Teachers are also secretaries in the model
            password="teacher123",
            academic_title="Prof. Dr.",
            auth_provider="local"
        ),
        User(
            email="teacher2@usv.ro",
            first_name="Elena",
            last_name="Dumitrescu",
            role=UserRole.SECRETARY,
            password="teacher123",
            academic_title="Conf. Dr.",
            auth_provider="local"
        ),
        User(
            email="teacher3@usv.ro",
            first_name="Mihai",
            last_name="Georgescu",
            role=UserRole.SECRETARY,
            password="teacher123",
            academic_title="Lect. Dr.",
            auth_provider="local"
        )
    ]
    
    # Student users
    students = [
        User(
            email="student1@student.usv.ro",
            first_name="Andrei",
            last_name="Munteanu",
            role=UserRole.STUDENT,
            password="student123",
            auth_provider="local"
        ),
        User(
            email="student2@student.usv.ro",
            first_name="Ana",
            last_name="Popa",
            role=UserRole.STUDENT,
            password="student123",
            auth_provider="local"
        ),
        User(
            email="student3@student.usv.ro",
            first_name="Cristian",
            last_name="Stanescu",
            role=UserRole.STUDENT,
            password="student123",
            auth_provider="local"
        ),
        User(
            email="student4@student.usv.ro",
            first_name="Diana",
            last_name="Vasilescu",
            role=UserRole.STUDENT,
            password="student123",
            auth_provider="local"
        ),
        User(
            email="student5@student.usv.ro",
            first_name="Bogdan",
            last_name="Radulescu",
            role=UserRole.STUDENT,
            password="student123",
            auth_provider="local"
        )
    ]
    
    # Google Auth test user
    google_user = User(
        email="test.google@student.usv.ro",
        first_name="Test",
        last_name="Google",
        role=UserRole.STUDENT,
        google_id="test_google_id",
        profile_picture="https://ui-avatars.com/api/?name=Test+Google&background=random",
        auth_provider="google"
    )
    
    # Add all users to the database
    db.session.add(admin)
    db.session.add(secretary1)
    db.session.add(secretary2)
    
    for teacher in teachers:
        db.session.add(teacher)
    
    for student in students:
        db.session.add(student)
    
    db.session.add(google_user)
    db.session.commit()
    
    return {
        'admin': admin,
        'secretaries': [secretary1, secretary2],
        'teachers': teachers,
        'students': students,
        'google_user': google_user
    }

def populate_rooms():
    """Populate database with sample rooms"""
    print("Populating rooms...")
    
    rooms = [
        Room(
            name="A101",
            capacity=30,
            building="Corp A",
            floor=1,
            room_type="lecture",
            features="projector,whiteboard,computers"
        ),
        Room(
            name="A102",
            capacity=25,
            building="Corp A",
            floor=1,
            room_type="seminar",
            features="projector,whiteboard"
        ),
        Room(
            name="B201",
            capacity=100,
            building="Corp B",
            floor=2,
            room_type="lecture",
            features="projector,whiteboard,sound_system"
        ),
        Room(
            name="B202",
            capacity=20,
            building="Corp B",
            floor=2,
            room_type="lab",
            features="projector,whiteboard,computers,specialized_equipment"
        ),
        Room(
            name="C301",
            capacity=50,
            building="Corp C",
            floor=3,
            room_type="lecture",
            features="projector,whiteboard"
        ),
        Room(
            name="C302",
            capacity=15,
            building="Corp C",
            floor=3,
            room_type="meeting",
            features="whiteboard,round_table"
        ),
        Room(
            name="D101",
            capacity=40,
            building="Corp D",
            floor=1,
            room_type="lab",
            features="projector,whiteboard,computers"
        ),
        Room(
            name="D102",
            capacity=35,
            building="Corp D",
            floor=1,
            room_type="seminar",
            features="projector,whiteboard"
        )
    ]
    
    for room in rooms:
        db.session.add(room)
    
    db.session.commit()
    return rooms

def populate_schedules(rooms):
    """Populate database with sample schedules for rooms"""
    print("Populating schedules...")
    
    current_semester = "2024-2025-2"  # Second semester of 2024-2025 academic year
    
    subjects = [
        "Programare Orientată pe Obiecte",
        "Baze de Date",
        "Rețele de Calculatoare",
        "Inteligență Artificială",
        "Sisteme de Operare",
        "Algoritmi și Structuri de Date",
        "Matematică Discretă",
        "Arhitectura Calculatoarelor",
        "Ingineria Programării",
        "Grafică pe Calculator"
    ]
    
    professors = [
        "Prof. Dr. Alexandru Popescu",
        "Conf. Dr. Elena Dumitrescu",
        "Lect. Dr. Mihai Georgescu",
        "Prof. Dr. Ioana Marinescu",
        "Conf. Dr. Radu Stoica"
    ]
    
    groups = ["MI1", "MI2", "MI3", "IA1", "IA2", "IA3", "CSIE1", "CSIE2"]
    
    schedules = []
    
    for room in rooms:
        # Create 3-5 schedules per room
        num_schedules = random.randint(3, 5)
        
        for _ in range(num_schedules):
            day = random.choice(list(DayOfWeek))
            
            # Generate start time between 8:00 and 16:00
            start_hour = random.randint(8, 16)
            start = time(start_hour, 0)
            
            # End time is 2 hours after start time
            end_hour = start_hour + 2
            end = time(end_hour, 0)
            
            subject = random.choice(subjects)
            professor = random.choice(professors)
            group = random.choice(groups)
            
            schedule = Schedule(
                room_id=room.id,
                day_of_week=day,
                start_time=start,
                end_time=end,
                subject=subject,
                professor=professor,
                group_name=group,
                semester=current_semester
            )
            
            db.session.add(schedule)
            schedules.append(schedule)
    
    db.session.commit()
    return schedules

def populate_reservations(users, rooms):
    """Populate database with sample reservations"""
    print("Populating reservations...")
    
    purposes = [
        "Examen la Programare Orientată pe Obiecte",
        "Laborator suplimentar de Baze de Date",
        "Consultații pentru proiect",
        "Prezentare proiect de semestru",
        "Seminar recuperare",
        "Întâlnire grup de studiu",
        "Workshop programare",
        "Sesiune de pregătire pentru examen"
    ]
    
    today = date.today()
    
    # Create some reservations for each student
    reservations = []
    
    for student in users['students']:
        # Create 1-3 reservations per student
        num_reservations = random.randint(1, 3)
        
        for _ in range(num_reservations):
            # Random date in the next 30 days
            reservation_date = today + timedelta(days=random.randint(1, 30))
            
            # Random start time between 8:00 and 18:00
            start_hour = random.randint(8, 18)
            start = time(start_hour, 0)
            
            # End time is 1-2 hours after start time
            duration = random.randint(1, 2)
            end_hour = start_hour + duration
            end = time(end_hour, 0)
            
            room = random.choice(rooms)
            purpose = random.choice(purposes)
            
            reservation = Reservation(
                user_id=student.id,
                room_id=room.id,
                purpose=purpose,
                date=reservation_date,
                start_time=start,
                end_time=end
            )
            
            db.session.add(reservation)
            reservations.append(reservation)
    
    db.session.commit()
    
    # Approve or reject some reservations
    for reservation in reservations:
        # 70% chance of being approved, 20% chance of being rejected, 10% chance of staying pending
        status_chance = random.random()
        
        if status_chance < 0.7:
            # Approve reservation
            secretary = random.choice(users['secretaries'])
            reservation.approve(secretary.id)
        elif status_chance < 0.9:
            # Reject reservation
            secretary = random.choice(users['secretaries'])
            reasons = [
                "Sala este deja rezervată în acest interval",
                "Sala nu este disponibilă în ziua respectivă",
                "Cerere incompletă",
                "Scopul rezervării nu este clar"
            ]
            reason = random.choice(reasons)
            reservation.reject(secretary.id, reason)
    
    db.session.commit()
    return reservations

def main():
    with app.app_context():
        # Check if database already has data
        if User.query.count() > 0:
            print("Database already has users. Clearing and repopulating...")
            
            # Clear database
            print("Clearing database...")
            db.drop_all()
            db.create_all()
        
        # Populate database
        users = populate_users()
        rooms = populate_rooms()
        schedules = populate_schedules(rooms)
        reservations = populate_reservations(users, rooms)
        
        print(f"Database populated successfully!")
        print(f"Created {len(users['students']) + len(users['teachers']) + len(users['secretaries']) + 2} users")
        print(f"Created {len(rooms)} rooms")
        print(f"Created {len(schedules)} schedules")
        print(f"Created {len(reservations)} reservations")

if __name__ == "__main__":
    main()
