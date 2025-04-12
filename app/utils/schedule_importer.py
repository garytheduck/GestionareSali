import pandas as pd
from datetime import datetime, time
from app.models.room import Room
from app.models.schedule import Schedule, DayOfWeek
from app import db
from app.utils.usv_api_client import import_rooms_from_usv, import_schedule_from_usv

def import_schedule_from_usv_api(semester):
    """
    Import schedule from USV API
    
    Args:
        semester: Current semester string (e.g., "2023-2024-1")
        
    Returns:
        dict: Statistics about the import process
    """
    # First import rooms from USV API
    rooms_stats = import_rooms_from_usv()
    
    # Then import schedules
    schedule_stats = import_schedule_from_usv(semester)
    
    # Combine statistics
    combined_stats = {
        'rooms_imported': rooms_stats['created'],
        'rooms_updated': rooms_stats['updated'],
        'rooms_errors': rooms_stats['errors'],
        'schedules_processed': schedule_stats['processed'],
        'schedules_skipped': schedule_stats['skipped'],
        'schedules_errors': schedule_stats['errors'],
        'error_details': rooms_stats['error_details'] + schedule_stats['error_details']
    }
    
    return combined_stats


def import_schedule_from_excel(file_io, filename, semester):
    """
    Import schedule from Excel or CSV file
    
    Args:
        file_io: File-like object containing the Excel/CSV data
        filename: Original filename (used to determine file type)
        semester: Current semester string (e.g., "2023-2024-1")
        
    Returns:
        dict: Statistics about the import process
    """
    # Determine file type
    if filename.endswith('.csv'):
        df = pd.read_csv(file_io)
    else:  # Excel file
        df = pd.read_excel(file_io)
    
    # Validate required columns
    required_columns = [
        'room_name', 'day_of_week', 'start_time', 'end_time', 
        'subject', 'professor', 'group_name'
    ]
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Lipsesc coloanele obligatorii: {', '.join(missing_columns)}")
    
    # Statistics
    stats = {
        'total_rows': len(df),
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'error_details': []
    }
    
    # Deactivate all existing schedules for this semester
    Schedule.query.filter_by(semester=semester).update({Schedule.is_active: False})
    db.session.commit()
    
    # Process each row
    for index, row in df.iterrows():
        try:
            # Get or create room
            room_name = str(row['room_name']).strip()
            room = Room.query.filter_by(name=room_name).first()
            
            if not room:
                # Create a new room with default values
                room = Room(
                    name=room_name,
                    capacity=0,  # Default value
                    building='Unknown',  # Default value
                    floor=0,  # Default value
                    room_type='Unknown'  # Default value
                )
                db.session.add(room)
                db.session.flush()  # Get ID without committing
            
            # Parse day of week
            day_str = str(row['day_of_week']).strip().lower()
            try:
                day_of_week = DayOfWeek(day_str)
            except ValueError:
                # Try to map common day names to enum values
                day_mapping = {
                    'luni': DayOfWeek.MONDAY,
                    'marti': DayOfWeek.TUESDAY,
                    'miercuri': DayOfWeek.WEDNESDAY,
                    'joi': DayOfWeek.THURSDAY,
                    'vineri': DayOfWeek.FRIDAY,
                    'sambata': DayOfWeek.SATURDAY,
                    'duminica': DayOfWeek.SUNDAY,
                    'monday': DayOfWeek.MONDAY,
                    'tuesday': DayOfWeek.TUESDAY,
                    'wednesday': DayOfWeek.WEDNESDAY,
                    'thursday': DayOfWeek.THURSDAY,
                    'friday': DayOfWeek.FRIDAY,
                    'saturday': DayOfWeek.SATURDAY,
                    'sunday': DayOfWeek.SUNDAY,
                }
                
                if day_str in day_mapping:
                    day_of_week = day_mapping[day_str]
                else:
                    raise ValueError(f"Ziua săptămânii nevalidă: {day_str}")
            
            # Parse times
            start_time_str = str(row['start_time']).strip()
            end_time_str = str(row['end_time']).strip()
            
            # Handle different time formats
            try:
                # Try HH:MM format
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
            except ValueError:
                try:
                    # Try H:MM format
                    start_time = datetime.strptime(start_time_str, '%-H:%M').time()
                except ValueError:
                    raise ValueError(f"Format oră de început invalid: {start_time_str}")
            
            try:
                # Try HH:MM format
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
            except ValueError:
                try:
                    # Try H:MM format
                    end_time = datetime.strptime(end_time_str, '%-H:%M').time()
                except ValueError:
                    raise ValueError(f"Format oră de sfârșit invalid: {end_time_str}")
            
            # Get other fields
            subject = str(row['subject']).strip()
            professor = str(row['professor']).strip() if not pd.isna(row['professor']) else None
            group_name = str(row['group_name']).strip() if not pd.isna(row['group_name']) else None
            
            # Create or update schedule
            schedule = Schedule.query.filter_by(
                room_id=room.id,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
                semester=semester
            ).first()
            
            if schedule:
                # Update existing schedule
                schedule.subject = subject
                schedule.professor = professor
                schedule.group_name = group_name
                schedule.is_active = True
            else:
                # Create new schedule
                schedule = Schedule(
                    room_id=room.id,
                    day_of_week=day_of_week,
                    start_time=start_time,
                    end_time=end_time,
                    subject=subject,
                    professor=professor,
                    group_name=group_name,
                    semester=semester
                )
                db.session.add(schedule)
            
            stats['processed'] += 1
            
        except Exception as e:
            stats['errors'] += 1
            stats['error_details'].append(f"Eroare la rândul {index + 2}: {str(e)}")
            stats['skipped'] += 1
    
    # Commit changes
    db.session.commit()
    
    return stats
