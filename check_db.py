from app import create_app, db
from app.models.room import Room
from app.models.schedule import Schedule, DayOfWeek
from app.models.user import User
from app.models.settings import InstitutionSettings
from app.models.reservation import Reservation

def safe_str(text):
    """Convert any string to ASCII to avoid encoding issues"""
    if text is None:
        return 'None'
    return str(text).encode('ascii', 'replace').decode('ascii')

app = create_app('development')

with app.app_context():
    # Check rooms
    rooms = Room.query.all()
    print(f"\n=== ROOMS ({len(rooms)} total) ===")
    for i, room in enumerate(rooms[:10]):  # Show first 10 rooms
        print(f"{i+1}. {room.name} (Building: {room.building}, USV ID: {room.usv_id})")
    if len(rooms) > 10:
        print(f"... and {len(rooms) - 10} more rooms")
    
    # Check schedules
    schedules = Schedule.query.all()
    print(f"\n=== SCHEDULES ({len(schedules)} total) ===")
    for i, schedule in enumerate(schedules[:10]):  # Show first 10 schedules
        room = db.session.get(Room, schedule.room_id)
        print(f"{i+1}. Room: {room.name}, Day: {schedule.day_of_week.name}")
        print(f"   Time: {schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}")
        print(f"   Subject: {safe_str(schedule.subject)}")
        # Avoid special characters in professor names
        if schedule.professor:
            print(f"   Professor: {safe_str(schedule.professor)}")
    if len(schedules) > 10:
        print(f"... and {len(schedules) - 10} more schedules")
    
    # Check users
    users = User.query.all()
    print(f"\n=== USERS ({len(users)} total) ===")
    for user in users:
        print(f"- {user.email} (Role: {user.role.name}, Google ID: {user.google_id})")
        print(f"  Name: {safe_str(user.first_name)} {safe_str(user.last_name)}")
    
    # Check settings
    settings = InstitutionSettings.query.first()
    print(f"\n=== INSTITUTION SETTINGS ===")
    if settings:
        print(f"Name: {safe_str(settings.name)}")
        print(f"Address: {safe_str(settings.address)}")
        print(f"Current Semester: {safe_str(settings.current_semester)}")
    else:
        print("No settings found")
    
    # Check reservations
    reservations = Reservation.query.all()
    print(f"\n=== RESERVATIONS ({len(reservations)} total) ===")
    for i, res in enumerate(reservations):
        print(f"{i+1}. Reference: {res.reference_number}, Status: {res.status.value}")
        user = db.session.get(User, res.user_id)
        room = db.session.get(Room, res.room_id)
        print(f"   User: {user.email}, Room: {room.name}")
        print(f"   Date: {res.date}, Time: {res.start_time.strftime('%H:%M')}-{res.end_time.strftime('%H:%M')}")
        print(f"   Purpose: {safe_str(res.purpose)}")
        if res.rejection_reason:
            print(f"   Rejection Reason: {safe_str(res.rejection_reason)}")
    
    # Check schedule statistics by day of week
    print(f"\n=== SCHEDULE STATISTICS BY DAY ===")
    for day in DayOfWeek:
        count = Schedule.query.filter_by(day_of_week=day).count()
        print(f"{day.name}: {count} schedules")
    
    # Check schedule statistics by building
    print(f"\n=== SCHEDULE STATISTICS BY BUILDING ===")
    buildings = db.session.query(Room.building, db.func.count(Schedule.id)).\
        join(Schedule, Schedule.room_id == Room.id).\
        group_by(Room.building).\
        order_by(db.func.count(Schedule.id).desc()).all()
    
    for building, count in buildings:
        print(f"{building}: {count} schedules")
