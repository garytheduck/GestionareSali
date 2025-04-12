from app import create_app, db
from app.models.room import Room
from app.models.schedule import Schedule, DayOfWeek
from app.models.user import User
from app.models.settings import InstitutionSettings

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
        room = Room.query.get(schedule.room_id)
        print(f"{i+1}. Room: {room.name}, Day: {schedule.day_of_week.name}, " +
              f"Time: {schedule.start_time.strftime('%H:%M')}-{schedule.end_time.strftime('%H:%M')}, " +
              f"Subject: {schedule.subject}, Professor: {schedule.professor}")
    if len(schedules) > 10:
        print(f"... and {len(schedules) - 10} more schedules")
    
    # Check users
    users = User.query.all()
    print(f"\n=== USERS ({len(users)} total) ===")
    for user in users:
        print(f"- {user.email} ({user.role.name})")
    
    # Check settings
    settings = InstitutionSettings.query.first()
    print(f"\n=== INSTITUTION SETTINGS ===")
    if settings:
        print(f"Name: {settings.name}")
        print(f"Address: {settings.address}")
        print(f"Current Semester: {settings.current_semester}")
    else:
        print("No settings found")
    
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
