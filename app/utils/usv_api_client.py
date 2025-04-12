import requests
import json
from datetime import datetime, time, timedelta
from app.models.room import Room
from app.models.schedule import Schedule, DayOfWeek
from app import db

class USVApiClient:
    """
    Client for interacting with the USV scheduling system API
    """
    BASE_URL = "https://orar.usv.ro/orar/vizualizare/data"
    
    @staticmethod
    def get_cadre():
        """Get all staff/teachers from USV API"""
        url = f"{USVApiClient.BASE_URL}/cadre.php?json"
        response = requests.get(url)
        return response.json()
    
    @staticmethod
    def get_sali():
        """Get all rooms from USV API"""
        url = f"{USVApiClient.BASE_URL}/sali.php?json"
        response = requests.get(url)
        return response.json()
    
    @staticmethod
    def get_facultati():
        """Get all faculties from USV API"""
        url = f"{USVApiClient.BASE_URL}/facultati.php?json"
        response = requests.get(url)
        return response.json()
    
    @staticmethod
    def get_subgrupe():
        """Get all subgroups from USV API"""
        url = f"{USVApiClient.BASE_URL}/subgrupe.php?json"
        response = requests.get(url)
        return response.json()
    
    @staticmethod
    def get_schedule_for_teacher(teacher_id):
        """Get schedule for a specific teacher"""
        url = f"{USVApiClient.BASE_URL}/orarSPG.php?ID={teacher_id}&mod=prof&json"
        response = requests.get(url)
        return response.json()
    
    @staticmethod
    def get_schedule_for_group(group_id):
        """Get schedule for a specific group"""
        url = f"{USVApiClient.BASE_URL}/orarSPG.php?ID={group_id}&mod=grupa&json"
        response = requests.get(url)
        return response.json()
    
    @staticmethod
    def convert_weekday(weekday_num):
        """Convert USV weekday number to DayOfWeek enum"""
        # USV API: 1=Monday, 2=Tuesday, ..., 7=Sunday
        day_mapping = {
            "1": DayOfWeek.MONDAY,
            "2": DayOfWeek.TUESDAY,
            "3": DayOfWeek.WEDNESDAY,
            "4": DayOfWeek.THURSDAY,
            "5": DayOfWeek.FRIDAY,
            "6": DayOfWeek.SATURDAY,
            "7": DayOfWeek.SUNDAY
        }
        return day_mapping.get(str(weekday_num), None)
    
    @staticmethod
    def convert_minutes_to_time(minutes_from_midnight):
        """Convert minutes from midnight to time object"""
        hours = int(minutes_from_midnight) // 60
        minutes = int(minutes_from_midnight) % 60
        return time(hour=hours, minute=minutes)


def import_rooms_from_usv():
    """
    Import rooms from USV API and update the database
    
    Returns:
        dict: Statistics about the import process
    """
    stats = {
        'total': 0,
        'created': 0,
        'updated': 0,
        'errors': 0,
        'error_details': []
    }
    
    try:
        rooms_data = USVApiClient.get_sali()
        stats['total'] = len(rooms_data)
        
        for room_data in rooms_data:
            try:
                room_id = room_data.get('id')
                room_name = room_data.get('shortName', '')
                building = room_data.get('building', '')
                long_name = room_data.get('longName', '')
                
                # Try to find existing room by USV ID or name
                room = Room.query.filter_by(usv_id=room_id).first()
                if not room:
                    room = Room.query.filter_by(name=room_name).first()
                
                if room:
                    # Update existing room
                    room.name = room_name
                    room.building = building
                    room.usv_id = room_id
                    room.description = long_name
                    stats['updated'] += 1
                else:
                    # Create new room with default values for required fields
                    room = Room(
                        name=room_name,
                        capacity=30,  # Default value
                        building=building,
                        floor=0,  # Default value
                        room_type='Unknown',  # Default value
                        features=None
                    )
                    room.usv_id = room_id
                    room.description = long_name
                    db.session.add(room)
                    stats['created'] += 1
                
            except Exception as e:
                stats['errors'] += 1
                stats['error_details'].append(f"Error processing room {room_data.get('id')}: {str(e)}")
        
        db.session.commit()
    
    except Exception as e:
        stats['errors'] += 1
        stats['error_details'].append(f"Error fetching rooms data: {str(e)}")
        db.session.rollback()
    
    return stats


def import_schedule_from_usv(semester):
    """
    Import schedule from USV API and update the database
    
    Args:
        semester: Current semester string (e.g., "2023-2024-1")
        
    Returns:
        dict: Statistics about the import process
    """
    stats = {
        'total_activities': 0,
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'error_details': []
    }
    
    try:
        # Deactivate all existing schedules for this semester
        Schedule.query.filter_by(semester=semester).update({Schedule.is_active: False})
        db.session.commit()
        
        # Get all teachers
        teachers = USVApiClient.get_cadre()
        
        # Process each teacher's schedule
        for teacher in teachers:
            try:
                teacher_id = teacher.get('id')
                teacher_name = f"{teacher.get('lastName', '')} {teacher.get('firstName', '')}"
                
                # Get teacher's schedule
                schedule_data = USVApiClient.get_schedule_for_teacher(teacher_id)
                
                if not schedule_data or len(schedule_data) < 1:
                    continue
                
                activities = schedule_data[0]  # First element contains activities
                stats['total_activities'] += len(activities)
                
                for activity in activities:
                    try:
                        # Extract activity data
                        room_id = activity.get('roomId')
                        room_name = activity.get('roomShortName', '')
                        weekday = activity.get('weekDay')
                        start_minutes = activity.get('startHour')
                        duration_minutes = activity.get('duration')
                        subject = activity.get('topicLongName', '')
                        subject_short = activity.get('topicShortName', '')
                        activity_type = activity.get('typeLongName', '')
                        
                        # Get or create room
                        room = Room.query.filter_by(usv_id=room_id).first()
                        if not room:
                            # Try by name
                            room = Room.query.filter_by(name=room_name).first()
                            
                        if not room:
                            # Create a new room with default values
                            room = Room(
                                name=room_name,
                                capacity=30,  # Default value
                                building=activity.get('roomBuilding', 'Unknown'),
                                floor=0,  # Default value
                                room_type='Unknown'  # Default value
                            )
                            room.usv_id = room_id
                            db.session.add(room)
                            db.session.flush()  # Get ID without committing
                        
                        # Convert day of week
                        day_of_week = USVApiClient.convert_weekday(weekday)
                        if not day_of_week:
                            raise ValueError(f"Invalid weekday: {weekday}")
                        
                        # Convert times
                        start_time = USVApiClient.convert_minutes_to_time(start_minutes)
                        
                        # Calculate end time
                        end_minutes = int(start_minutes) + int(duration_minutes)
                        end_time = USVApiClient.convert_minutes_to_time(end_minutes)
                        
                        # Determine group name
                        group_info = ""
                        if len(schedule_data) > 1 and activity.get('id') in schedule_data[1]:
                            group_info = ", ".join(schedule_data[1][activity.get('id')])
                        
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
                            schedule.subject = f"{subject} ({activity_type})"
                            schedule.professor = teacher_name
                            schedule.group_name = group_info
                            schedule.is_active = True
                        else:
                            # Create new schedule
                            schedule = Schedule(
                                room_id=room.id,
                                day_of_week=day_of_week,
                                start_time=start_time,
                                end_time=end_time,
                                subject=f"{subject} ({activity_type})",
                                professor=teacher_name,
                                group_name=group_info,
                                semester=semester
                            )
                            db.session.add(schedule)
                        
                        stats['processed'] += 1
                        
                    except Exception as e:
                        stats['errors'] += 1
                        stats['error_details'].append(f"Error processing activity {activity.get('id')}: {str(e)}")
                        stats['skipped'] += 1
                
            except Exception as e:
                stats['errors'] += 1
                stats['error_details'].append(f"Error processing teacher {teacher.get('id')}: {str(e)}")
        
        # Commit changes
        db.session.commit()
        
    except Exception as e:
        stats['errors'] += 1
        stats['error_details'].append(f"Error fetching data: {str(e)}")
        db.session.rollback()
    
    return stats
