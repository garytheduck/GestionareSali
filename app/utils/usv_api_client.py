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


def import_rooms_from_usv(force_recreate=True):
    """
    Import rooms from USV API and update the database
    
    Args:
        force_recreate (bool): If True, delete all existing rooms and recreate them
    
    Returns:
        dict: Statistics about the import process
    """
    stats = {
        'total': 0,
        'created': 0,
        'updated': 0,
        'errors': 0,
        'error_details': [],
        'rooms_imported': 0,
        'rooms_updated': 0,
        'rooms_deleted': 0
    }
    
    try:
        # Dacă force_recreate este True, ștergem toate sălile existente
        if force_recreate:
            try:
                # Salvăm sălile predefinite (id < 4) pentru a le păstra
                predefined_rooms = Room.query.filter(Room.id < 4).all()
                predefined_data = [{
                    'id': room.id,
                    'name': room.name,
                    'capacity': room.capacity,
                    'building': room.building,
                    'floor': room.floor,
                    'room_type': room.room_type,
                    'features': room.features,
                    'usv_id': room.usv_id,
                    'description': room.description,
                    'is_active': room.is_active
                } for room in predefined_rooms]
                
                # Ștergem toate sălile
                deleted_count = Room.query.delete()
                stats['rooms_deleted'] = deleted_count
                db.session.commit()
                
                # Recreăm sălile predefinite
                for room_data in predefined_data:
                    room = Room(
                        id=room_data['id'],
                        name=room_data['name'],
                        capacity=room_data['capacity'],
                        building=room_data['building'],
                        floor=room_data['floor'],
                        room_type=room_data['room_type'],
                        features=room_data['features'],
                        usv_id=room_data['usv_id'],
                        description=room_data['description'],
                        is_active=room_data['is_active']
                    )
                    db.session.add(room)
                db.session.commit()
                
                print(f"Deleted {deleted_count} rooms and recreated {len(predefined_data)} predefined rooms")
            except Exception as e:
                print(f"Error deleting rooms: {str(e)}")
                db.session.rollback()
                stats['errors'] += 1
                stats['error_details'].append(f"Error deleting rooms: {str(e)}")
        
        # Obținem datele de la API-ul USV
        rooms_data = USVApiClient.get_sali()
        stats['total'] = len(rooms_data)
        
        # Procesăm fiecare sală
        for room_data in rooms_data:
            try:
                room_id = room_data.get('id')
                room_name = room_data.get('shortName', '')
                building = room_data.get('building', '')
                long_name = room_data.get('longName', '')
                
                # Extrage informații suplimentare din numele și descrierea sălii
                floor, room_type, capacity, extracted_building = extract_room_info(room_name, long_name)
                
                # Încearcă să găsești sala după USV ID sau nume
                room = Room.query.filter_by(usv_id=room_id).first()
                if not room:
                    room = Room.query.filter_by(name=room_name).first()
                
                if room:
                    # Actualizează sala existentă
                    room.name = room_name
                    room.building = extracted_building if extracted_building else (building if building else 'USV')
                    room.floor = floor if floor is not None else 0
                    room.room_type = room_type if room_type else 'Sală de curs'
                    room.capacity = capacity if capacity and capacity > 0 else 30
                    room.usv_id = room_id
                    room.description = long_name
                    
                    stats['updated'] += 1
                    stats['rooms_updated'] += 1
                else:
                    # Creează o sală nouă cu valorile extrase
                    room = Room(
                        name=room_name,
                        capacity=capacity if capacity and capacity > 0 else 30,
                        building=extracted_building if extracted_building else (building if building else 'USV'),
                        floor=floor if floor is not None else 0,
                        room_type=room_type if room_type else 'Sală de curs',
                        features=None
                    )
                    room.usv_id = room_id
                    room.description = long_name
                    db.session.add(room)
                    stats['created'] += 1
                    stats['rooms_imported'] += 1
                
            except Exception as e:
                stats['errors'] += 1
                stats['error_details'].append(f"Error processing room {room_data.get('id')}: {str(e)}")
        
        db.session.commit()
        print(f"Import completed: {stats['created']} created, {stats['updated']} updated, {stats['errors']} errors")
    
    except Exception as e:
        stats['errors'] += 1
        stats['error_details'].append(f"Error fetching rooms data: {str(e)}")
        db.session.rollback()
        print(f"Import failed: {str(e)}")
    
    return stats


def extract_room_info(room_name, long_name):
    """
    Extrage informații despre sală din numele și descrierea acesteia.
    
    Args:
        room_name (str): Numele scurt al sălii (ex: 'C201', 'L004')
        long_name (str): Descrierea detaliată a sălii
        
    Returns:
        tuple: (floor, room_type, capacity, building)
    """
    floor = None
    room_type = None
    capacity = None
    building = None
    
    # Determină clădirea în funcție de prima literă a numelui sălii
    if room_name and len(room_name) > 0:
        first_letter = room_name[0].upper()
        if first_letter == 'A':
            building = 'Corp A'
        elif first_letter == 'B':
            building = 'Corp B'
        elif first_letter == 'C':
            building = 'Corp C'
        elif first_letter == 'D':
            building = 'Corp D'
        elif first_letter == 'E':
            building = 'Corp E'
        elif first_letter == 'H':
            building = 'Corp H'
        elif first_letter == 'J':
            building = 'Corp J'
        elif first_letter == 'K':
            building = 'Corp K'
        elif first_letter == 'L':
            building = 'Laborator'
        elif first_letter == 'S':
            building = 'Sala Sport'
        else:
            # Verifică dacă numele sălii conține informații despre clădire
            if 'Aula' in room_name:
                building = 'Aula'
            elif 'Bazin' in room_name:
                building = 'Bazin înot'
            elif 'Stadion' in room_name:
                building = 'Stadion'
            elif 'Amf' in room_name:
                building = 'Amfiteatru'
            else:
                building = 'USV'
    
    # Extrage etajul din numele sălii (ex: C201 -> etajul 2)
    if len(room_name) >= 2:
        # Încearcă să extragă etajul din a doua cifră a numelui
        try:
            if room_name[1].isdigit():
                floor = int(room_name[1])
            # Sau din prima cifră după prima literă
            elif len(room_name) >= 3 and room_name[2].isdigit():
                floor = int(room_name[2])
            # Sau din prima cifră din nume
            else:
                import re
                floor_match = re.search(r'\d', room_name)
                if floor_match:
                    floor = int(floor_match.group(0))
        except (ValueError, IndexError):
            pass
    
    # Extrage tipul sălii din prima literă a numelui sau din descriere
    if room_name and len(room_name) > 0:
        first_letter = room_name[0].upper()
        
        # Verifică dacă numele sălii conține o literă urmată de cifre (ex: A123, B201, C301)
        import re
        lab_pattern = re.match(r'^([A-Z])\d+', room_name)
        
        # Sălile cu litere A, B, C, D, E, H urmate de cifre sunt laboratoare
        if lab_pattern and first_letter in ['A', 'B', 'C', 'D', 'E', 'H']:
            room_type = 'Laborator'
        # Alte reguli specifice pentru tipuri de săli
        elif first_letter == 'L':
            room_type = 'Laborator'
        elif first_letter == 'S':
            room_type = 'Sală de seminar'
        elif first_letter == 'A' and not lab_pattern:
            room_type = 'Amfiteatru'
        elif first_letter == 'B' and not lab_pattern:
            room_type = 'Bibliotecă'
        else:
            # Verifică în descriere sau nume pentru indicii despre tipul sălii
            if 'Lab' in room_name or 'Lab' in long_name:
                room_type = 'Laborator'
            elif 'Amf' in room_name or 'Amfiteatru' in long_name:
                room_type = 'Amfiteatru'
            elif 'Curs' in room_name or 'Curs' in long_name:
                room_type = 'Sală de curs'
            elif 'Seminar' in room_name or 'Seminar' in long_name:
                room_type = 'Sală de seminar'
            elif 'Birou' in room_name or 'Birou' in long_name:
                room_type = 'Birou'
            else:
                room_type = 'Altele'
    
    # Încearcă să extragă capacitatea din descrierea detaliată
    if long_name:
        # Caută un număr în descriere care ar putea reprezenta capacitatea
        import re
        capacity_matches = re.findall(r'\b(\d+)\s*(locuri|persoane|studenti|capacity)\b', long_name, re.IGNORECASE)
        if capacity_matches:
            try:
                capacity = int(capacity_matches[0][0])
            except (ValueError, IndexError):
                pass
    
    # Dacă nu am găsit capacitatea, estimăm în funcție de tipul sălii
    if not capacity and room_type:
        if room_type == 'Amfiteatru':
            capacity = 100
        elif room_type == 'Sală de curs':
            capacity = 50
        elif room_type == 'Laborator':
            capacity = 30
        elif room_type == 'Sală de seminar':
            capacity = 25
        elif room_type == 'Birou':
            capacity = 5
        else:
            capacity = 20
    
    return floor, room_type, capacity, building


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
