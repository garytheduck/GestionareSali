"""
Script pentru verificarea datelor din toate tabelele bazei de date
"""
from app import create_app, db
from app.models.user import User, UserRole
from app.models.room import Room
from app.models.course import Course, ExamType
from app.models.group_leader import GroupLeader
from app.models.exam import Exam, ExamRegistration
from app.models.settings import InstitutionSettings
from app.models.schedule import Schedule, DayOfWeek
from app.models.reservation import Reservation
from sqlalchemy import inspect

def safe_str(text):
    """Convert any string to ASCII to avoid encoding issues"""
    if text is None:
        return 'None'
    return str(text).encode('ascii', 'replace').decode('ascii')

app = create_app()

with app.app_context():
    # Get all tables from SQLAlchemy metadata
    inspector = inspect(db.engine)
    all_tables = inspector.get_table_names()
    
    print(f"\n=== DATABASE TABLES ({len(all_tables)} total) ===")
    for table in all_tables:
        print(f"- {table}")
    
    # Check courses
    courses = Course.query.all()
    print(f"\n=== COURSES ({len(courses)} total) ===")
    for i, course in enumerate(courses[:10]):  # Show first 10 courses
        print(f"{i+1}. {safe_str(course.name)} (Code: {safe_str(course.code)}, Program: {safe_str(course.study_program)})")
        print(f"   Faculty: {safe_str(course.faculty)}, Department: {safe_str(course.department)}")
        print(f"   Year: {course.year_of_study}, Semester: {course.semester}, Credits: {course.credits}")
        print(f"   Group: {safe_str(course.group_name)}, Exam Type: {safe_str(course.exam_type)}")
    if len(courses) > 10:
        print(f"... and {len(courses) - 10} more courses")
    
    # Check group leaders
    group_leaders = GroupLeader.query.all()
    print(f"\n=== GROUP LEADERS ({len(group_leaders)} total) ===")
    for i, gl in enumerate(group_leaders[:10]):  # Show first 10 group leaders
        user = db.session.get(User, gl.user_id) if gl.user_id else None
        print(f"{i+1}. {safe_str(user.email) if user else 'Unknown'}")
        print(f"   Faculty: {safe_str(gl.faculty)}, Program: {safe_str(gl.study_program)}")
        print(f"   Year: {gl.year_of_study}, Semester: {gl.current_semester}")
        print(f"   Group: {safe_str(gl.group_name)}")
    if len(group_leaders) > 10:
        print(f"... and {len(group_leaders) - 10} more group leaders")
    
    # Check exams
    exams = Exam.query.all()
    print(f"\n=== EXAMS ({len(exams)} total) ===")
    for i, exam in enumerate(exams[:10]):  # Show first 10 exams
        course = db.session.get(Course, exam.course_id) if exam.course_id else None
        room = db.session.get(Room, exam.room_id) if exam.room_id else None
        print(f"{i+1}. Course: {safe_str(course.name) if course else 'Unknown'}")
        print(f"   Room: {safe_str(room.name) if room else 'Unknown'}")
        print(f"   Time: {exam.start_time.strftime('%Y-%m-%d %H:%M')} to {exam.end_time.strftime('%H:%M')}")
        print(f"   Type: {exam.exam_type}, Max Students: {exam.max_students}")
        print(f"   Semester: {exam.semester}, Academic Year: {exam.academic_year}")
    if len(exams) > 10:
        print(f"... and {len(exams) - 10} more exams")
    
    # Check exam registrations
    registrations = ExamRegistration.query.all()
    print(f"\n=== EXAM REGISTRATIONS ({len(registrations)} total) ===")
    for i, reg in enumerate(registrations[:10]):  # Show first 10 registrations
        exam = db.session.get(Exam, reg.exam_id) if reg.exam_id else None
        student = db.session.get(User, reg.student_id) if reg.student_id else None
        course = db.session.get(Course, exam.course_id) if exam and exam.course_id else None
        print(f"{i+1}. Student: {safe_str(student.email) if student else 'Unknown'}")
        print(f"   Exam: {safe_str(course.name) if course else 'Unknown'}")
        print(f"   Status: {reg.status}")
    if len(registrations) > 10:
        print(f"... and {len(registrations) - 10} more registrations")
    
    # Check users
    users = User.query.all()
    print(f"\n=== USERS ({len(users)} total) ===")
    role_counts = {}
    for user in users:
        role_name = user.role.name if user.role else 'Unknown'
        role_counts[role_name] = role_counts.get(role_name, 0) + 1
    
    for role, count in role_counts.items():
        print(f"- {role}: {count} users")
    
    for i, user in enumerate(users[:10]):  # Show first 10 users
        print(f"{i+1}. {user.email} (Role: {user.role.name if user.role else 'Unknown'})")
        print(f"   Name: {safe_str(user.first_name)} {safe_str(user.last_name)}")
    if len(users) > 10:
        print(f"... and {len(users) - 10} more users")
    
    # Check rooms
    rooms = Room.query.all()
    print(f"\n=== ROOMS ({len(rooms)} total) ===")
    for i, room in enumerate(rooms[:10]):  # Show first 10 rooms
        print(f"{i+1}. {safe_str(room.name)} (Building: {safe_str(room.building)}, Capacity: {room.capacity})")
    if len(rooms) > 10:
        print(f"... and {len(rooms) - 10} more rooms")
    
    # Check settings
    settings = InstitutionSettings.query.first()
    print(f"\n=== INSTITUTION SETTINGS ===")
    if settings:
        print(f"Name: {safe_str(settings.name)}")
        print(f"Address: {safe_str(settings.address)}")
        print(f"Current Semester: {safe_str(settings.current_semester)}")
    else:
        print("No settings found")
    
    # Check schedules
    schedules = Schedule.query.all()
    print(f"\n=== SCHEDULES ({len(schedules)} total) ===")
    for i, schedule in enumerate(schedules[:5]):  # Show first 5 schedules
        room = db.session.get(Room, schedule.room_id) if schedule.room_id else None
        print(f"{i+1}. Room: {room.name if room else 'Unknown'}, Day: {schedule.day_of_week.name if schedule.day_of_week else 'Unknown'}")
        print(f"   Time: {schedule.start_time.strftime('%H:%M') if schedule.start_time else 'Unknown'}-{schedule.end_time.strftime('%H:%M') if schedule.end_time else 'Unknown'}")
        print(f"   Subject: {safe_str(schedule.subject)}")
    if len(schedules) > 5:
        print(f"... and {len(schedules) - 5} more schedules")
    
    # Check reservations
    reservations = Reservation.query.all()
    print(f"\n=== RESERVATIONS ({len(reservations)} total) ===")
    for i, res in enumerate(reservations[:5]):  # Show first 5 reservations
        user = db.session.get(User, res.user_id) if res.user_id else None
        room = db.session.get(Room, res.room_id) if res.room_id else None
        print(f"{i+1}. User: {user.email if user else 'Unknown'}, Room: {room.name if room else 'Unknown'}")
        print(f"   Date: {res.date}, Time: {res.start_time.strftime('%H:%M') if res.start_time else 'Unknown'}-{res.end_time.strftime('%H:%M') if res.end_time else 'Unknown'}")
    if len(reservations) > 5:
        print(f"... and {len(reservations) - 5} more reservations")
    
    # Summary
    print("\n=== DATABASE SUMMARY ===")
    print(f"- Tables: {len(all_tables)}")
    print(f"- Courses: {len(courses)}")
    print(f"- Group Leaders: {len(group_leaders)}")
    print(f"- Exams: {len(exams)}")
    print(f"- Exam Registrations: {len(registrations)}")
    print(f"- Users: {len(users)}")
    print(f"- Rooms: {len(rooms)}")
    print(f"- Schedules: {len(schedules)}")
    print(f"- Reservations: {len(reservations)}")
