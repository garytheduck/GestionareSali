"""
Client pentru API-ul sistemului Orar, cu suport pentru fallback la date mock
"""
import os
import json
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# URL-uri API pentru sistemul Orar (se vor configura din variabile de mediu)
ORAR_API_BASE_URL = os.environ.get('ORAR_API_BASE_URL', 'http://api.orar.usv.ro/v1')
ORAR_API_KEY = os.environ.get('ORAR_API_KEY', '')

# Endpoint-uri specifice
DISCIPLINES_ENDPOINT = '/disciplines'
TEACHERS_ENDPOINT = '/teachers'
ROOMS_ENDPOINT = '/rooms'
SCHEDULE_ENDPOINT = '/schedule'

# Date mock pentru fallback
MOCK_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'mock_data')
os.makedirs(MOCK_DATA_DIR, exist_ok=True)

class OrarClient:
    """Client pentru interacțiunea cu API-ul sistemului Orar"""
    
    def __init__(self, use_mock: bool = False):
        """
        Inițializează clientul
        
        Args:
            use_mock (bool): Dacă True, va folosi date mock în loc de apeluri API reale
        """
        self.use_mock = use_mock
        self.base_url = ORAR_API_BASE_URL
        self.api_key = ORAR_API_KEY
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_disciplines(self, faculty: str = None, program: str = None, year: int = None, 
                      semester: str = None, group: str = None) -> List[Dict[str, Any]]:
        """
        Obține lista de discipline filtrate după criteriile specificate
        
        Args:
            faculty: Facultatea (ex: "FIESC")
            program: Programul de studiu (ex: "Calculatoare")
            year: Anul de studiu (1-4)
            semester: Semestrul ("1" sau "2")
            group: Numele grupei (ex: "3211A")
            
        Returns:
            List[Dict[str, Any]]: Lista de discipline
        """
        try:
            if self.use_mock:
                return self._get_mock_data('disciplines.json')
            
            # Construim parametrii de query
            params = {}
            if faculty:
                params['faculty'] = faculty
            if program:
                params['program'] = program
            if year:
                params['year'] = year
            if semester:
                params['semester'] = semester
            if group:
                params['group'] = group
            
            # Facem request-ul
            url = f"{self.base_url}{DISCIPLINES_ENDPOINT}"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json().get('data', [])
            else:
                logger.warning(f"Failed to get disciplines: {response.status_code} - {response.text}")
                # Fallback la date mock în caz de eșec
                return self._get_mock_data('disciplines.json')
                
        except Exception as e:
            logger.error(f"Error getting disciplines: {str(e)}")
            # Fallback la date mock în caz de excepție
            return self._get_mock_data('disciplines.json')
    
    def get_teachers(self, faculty: str = None, department: str = None) -> List[Dict[str, Any]]:
        """
        Obține lista cadrelor didactice, opțional filtrate după facultate sau departament
        
        Args:
            faculty: Facultatea (ex: "FIESC")
            department: Departamentul
            
        Returns:
            List[Dict[str, Any]]: Lista cadrelor didactice
        """
        try:
            if self.use_mock:
                return self._get_mock_data('teachers.json')
            
            # Construim parametrii de query
            params = {}
            if faculty:
                params['faculty'] = faculty
            if department:
                params['department'] = department
            
            # Facem request-ul
            url = f"{self.base_url}{TEACHERS_ENDPOINT}"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json().get('data', [])
            else:
                logger.warning(f"Failed to get teachers: {response.status_code} - {response.text}")
                # Fallback la date mock în caz de eșec
                return self._get_mock_data('teachers.json')
                
        except Exception as e:
            logger.error(f"Error getting teachers: {str(e)}")
            # Fallback la date mock în caz de excepție
            return self._get_mock_data('teachers.json')
    
    def get_rooms(self, building: str = None, floor: int = None, room_type: str = None) -> List[Dict[str, Any]]:
        """
        Obține lista sălilor disponibile, opțional filtrate după clădire, etaj sau tip
        
        Args:
            building: Clădirea (ex: "C")
            floor: Etajul
            room_type: Tipul sălii (ex: "laboratory", "classroom")
            
        Returns:
            List[Dict[str, Any]]: Lista sălilor
        """
        try:
            if self.use_mock:
                return self._get_mock_data('rooms.json')
            
            # Construim parametrii de query
            params = {}
            if building:
                params['building'] = building
            if floor is not None:
                params['floor'] = floor
            if room_type:
                params['room_type'] = room_type
            
            # Facem request-ul
            url = f"{self.base_url}{ROOMS_ENDPOINT}"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return response.json().get('data', [])
            else:
                logger.warning(f"Failed to get rooms: {response.status_code} - {response.text}")
                # Fallback la date mock în caz de eșec
                return self._get_mock_data('rooms.json')
                
        except Exception as e:
            logger.error(f"Error getting rooms: {str(e)}")
            # Fallback la date mock în caz de excepție
            return self._get_mock_data('rooms.json')
    
    def _get_mock_data(self, filename: str) -> List[Dict[str, Any]]:
        """
        Obține date mock din fișierul specificat
        
        Args:
            filename: Numele fișierului mock
            
        Returns:
            List[Dict[str, Any]]: Datele mock
        """
        file_path = os.path.join(MOCK_DATA_DIR, filename)
        
        # Verifică dacă există fișierul, altfel îl creează cu date mock default
        if not os.path.exists(file_path):
            self._create_mock_data(filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading mock data from {filename}: {str(e)}")
            # Returnăm o listă goală în caz de eroare
            return []
    
    def _create_mock_data(self, filename: str):
        """
        Creează date mock pentru un anumit tip de fișier
        
        Args:
            filename: Numele fișierului care va fi creat
        """
        mock_data = []
        
        if filename == 'disciplines.json':
            mock_data = [
                {
                    "id": 1,
                    "code": "C101",
                    "name": "Programare în C++",
                    "faculty": "FIESC",
                    "department": "Calculatoare",
                    "study_program": "Calculatoare",
                    "year_of_study": 1,
                    "semester": "1",
                    "credits": 5,
                    "group_name": "3111A",
                    "exam_type": "exam",
                    "teacher": {
                        "id": 1,
                        "name": "Prof. Dr. Ion Popescu",
                        "email": "ion.popescu@usm.ro"
                    }
                },
                {
                    "id": 2,
                    "code": "C102",
                    "name": "Structuri de date și algoritmi",
                    "faculty": "FIESC",
                    "department": "Calculatoare",
                    "study_program": "Calculatoare",
                    "year_of_study": 1,
                    "semester": "1",
                    "credits": 6,
                    "group_name": "3111A",
                    "exam_type": "exam",
                    "teacher": {
                        "id": 2,
                        "name": "Conf. Dr. Maria Ionescu",
                        "email": "maria.ionescu@usm.ro"
                    }
                },
                {
                    "id": 3,
                    "code": "C201",
                    "name": "Programare web",
                    "faculty": "FIESC",
                    "department": "Calculatoare",
                    "study_program": "Calculatoare",
                    "year_of_study": 2,
                    "semester": "1",
                    "credits": 5,
                    "group_name": "3211A",
                    "exam_type": "colloquium",
                    "teacher": {
                        "id": 3,
                        "name": "Șef lucr. Dr. Alexandru Munteanu",
                        "email": "alexandru.munteanu@usm.ro"
                    }
                },
                {
                    "id": 4,
                    "code": "I201",
                    "name": "Sisteme de operare",
                    "faculty": "FIESC",
                    "department": "Automatică",
                    "study_program": "Automatică și Informatică Aplicată",
                    "year_of_study": 2,
                    "semester": "1",
                    "credits": 4,
                    "group_name": "3121A",
                    "exam_type": "exam",
                    "teacher": {
                        "id": 4,
                        "name": "Prof. Dr. Ioana Petrescu",
                        "email": "ioana.petrescu@usm.ro"
                    }
                },
                {
                    "id": 5,
                    "code": "C301",
                    "name": "Inteligență artificială",
                    "faculty": "FIESC",
                    "department": "Calculatoare",
                    "study_program": "Calculatoare",
                    "year_of_study": 3,
                    "semester": "1",
                    "credits": 5,
                    "group_name": "3311A",
                    "exam_type": "project",
                    "teacher": {
                        "id": 5,
                        "name": "Prof. Dr. Vasile Popovici",
                        "email": "vasile.popovici@usm.ro"
                    }
                }
            ]
        elif filename == 'teachers.json':
            mock_data = [
                {
                    "id": 1,
                    "academic_title": "Prof. Dr.",
                    "first_name": "Ion",
                    "last_name": "Popescu",
                    "email": "ion.popescu@usm.ro",
                    "faculty": "FIESC",
                    "department": "Calculatoare"
                },
                {
                    "id": 2,
                    "academic_title": "Conf. Dr.",
                    "first_name": "Maria",
                    "last_name": "Ionescu",
                    "email": "maria.ionescu@usm.ro",
                    "faculty": "FIESC",
                    "department": "Calculatoare"
                },
                {
                    "id": 3,
                    "academic_title": "Șef lucr. Dr.",
                    "first_name": "Alexandru",
                    "last_name": "Munteanu",
                    "email": "alexandru.munteanu@usm.ro",
                    "faculty": "FIESC",
                    "department": "Calculatoare"
                },
                {
                    "id": 4,
                    "academic_title": "Prof. Dr.",
                    "first_name": "Ioana",
                    "last_name": "Petrescu",
                    "email": "ioana.petrescu@usm.ro",
                    "faculty": "FIESC",
                    "department": "Automatică"
                },
                {
                    "id": 5,
                    "academic_title": "Prof. Dr.",
                    "first_name": "Vasile",
                    "last_name": "Popovici",
                    "email": "vasile.popovici@usm.ro",
                    "faculty": "FIESC",
                    "department": "Calculatoare"
                }
            ]
        elif filename == 'rooms.json':
            mock_data = [
                {
                    "id": 1,
                    "name": "C101",
                    "building": "C",
                    "floor": 1,
                    "capacity": 30,
                    "room_type": "laboratory",
                    "features": "Computers, Projector"
                },
                {
                    "id": 2,
                    "name": "C201",
                    "building": "C",
                    "floor": 2,
                    "capacity": 100,
                    "room_type": "lecture_hall",
                    "features": "Projector, Audio system"
                },
                {
                    "id": 3,
                    "name": "C301",
                    "building": "C",
                    "floor": 3,
                    "capacity": 25,
                    "room_type": "laboratory",
                    "features": "Computers, Smartboard"
                },
                {
                    "id": 4,
                    "name": "D110",
                    "building": "D",
                    "floor": 1,
                    "capacity": 40,
                    "room_type": "classroom",
                    "features": "Projector"
                },
                {
                    "id": 5,
                    "name": "B101",
                    "building": "B",
                    "floor": 1,
                    "capacity": 150,
                    "room_type": "lecture_hall",
                    "features": "Projector, Audio system, Recording equipment"
                }
            ]
        
        # Salvăm datele mock în fișier
        file_path = os.path.join(MOCK_DATA_DIR, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(mock_data, f, ensure_ascii=False, indent=2)
