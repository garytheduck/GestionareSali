import requests
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User, UserRole

external_api_bp = Blueprint('external_api', __name__)

@external_api_bp.route('/teachers', methods=['GET'])
@jwt_required()
def get_teachers():
    """Get all teachers from the USV API"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'Acces interzis'}), 403
    
    try:
        # Fetch teachers from USV API
        response = requests.get('https://orar.usv.ro/orar/vizualizare/data/cadre.php?json')
        
        if response.status_code != 200:
            return jsonify({'message': 'Eroare la obținerea datelor de la API-ul USV'}), 500
        
        teachers_data = response.json()
        
        # Format teachers for frontend
        formatted_teachers = []
        for teacher in teachers_data:
            # Skip entries with null lastName or firstName
            if not teacher['lastName'] or not teacher['firstName']:
                continue
                
            # Create full name with academic title if available
            full_name = f"{teacher['lastName']} {teacher['firstName']}".strip()
            
            formatted_teachers.append({
                'id': teacher['id'],
                'name': full_name,
                'email': teacher['emailAddress'] or '',
                'facultyName': teacher['facultyName'] or '',
                'departmentName': teacher['departmentName'] or '',
                'available': True
            })
        
        return jsonify({
            'assistants': formatted_teachers
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Eroare: {str(e)}'}), 500
