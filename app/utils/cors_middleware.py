from flask import Flask, request, jsonify

def add_cors_headers(response):
    """Add CORS headers to all responses"""
    # Obținem originea cererii
    origin = request.headers.get('Origin', '*')
    
    # Verificăm dacă headerele CORS au fost deja adăugate
    if 'Access-Control-Allow-Origin' not in response.headers:
        # Permitem explicit originea localhost:3000 pentru dezvoltare
        if origin in ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://127.0.0.1:50002']:
            response.headers['Access-Control-Allow-Origin'] = origin
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'
            
        # Folosim set în loc de add pentru a evita duplicate
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,X-CSRF-Token'
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS,PATCH'
        response.headers['Access-Control-Max-Age'] = '3600'
    
    return response

def setup_cors_middleware(app):
    """Setup CORS middleware for Flask app"""
    
    @app.after_request
    def after_request(response):
        return add_cors_headers(response)
    
    # Handle all OPTIONS requests globally
    @app.before_request
    def handle_options_method():
        if request.method == 'OPTIONS':
            response = app.make_default_options_response()
            return add_cors_headers(response)
            
    # Adăugăm și handlerul original pentru compatibilitate
    @app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def options_handler(path):
        """Handle OPTIONS requests for CORS preflight"""
        response = jsonify({'status': 'ok'})
        return add_cors_headers(response)
