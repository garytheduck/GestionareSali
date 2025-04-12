from app.models.schedule import Schedule, DayOfWeek
from app.models.reservation import Reservation, ReservationStatus
from app.models.settings import InstitutionSettings
from datetime import datetime, time

def check_room_availability(room_id, date, start_time, end_time):
    """
    Check if a room is available for the given time slot
    
    Args:
        room_id: ID of the room
        date: Date object for the reservation
        start_time: Time object for the start time
        end_time: Time object for the end time
        
    Returns:
        tuple: (is_available, conflict_message)
    """
    # Get day of week for the given date
    day_of_week = DayOfWeek(date.strftime('%A').lower())
    
    # Get institution settings for working hours
    settings = InstitutionSettings.get_settings()
    
    # Check if the requested time is within working hours
    if start_time < settings.working_hours_start:
        return False, "Ora de început este înainte de programul de lucru"
    
    if end_time > settings.working_hours_end:
        return False, "Ora de sfârșit este după programul de lucru"
    
    # Check for conflicts with regular schedule
    schedule_conflicts = Schedule.query.filter(
        Schedule.room_id == room_id,
        Schedule.day_of_week == day_of_week,
        Schedule.is_active == True
    ).all()
    
    for schedule in schedule_conflicts:
        # Check if there's an overlap
        if (start_time < schedule.end_time and end_time > schedule.start_time):
            return False, f"Conflict cu orarul regulat: {schedule.subject} ({schedule.start_time.strftime('%H:%M')} - {schedule.end_time.strftime('%H:%M')})"
    
    # Check for conflicts with approved reservations
    reservation_conflicts = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.date == date,
        Reservation.status == ReservationStatus.APPROVED
    ).all()
    
    for reservation in reservation_conflicts:
        # Check if there's an overlap
        if (start_time < reservation.end_time and end_time > reservation.start_time):
            return False, f"Conflict cu o rezervare existentă: {reservation.reference_number} ({reservation.start_time.strftime('%H:%M')} - {reservation.end_time.strftime('%H:%M')})"
    
    return True, None
