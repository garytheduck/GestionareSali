from flask import Flask, request, jsonify

def add_cors_headers(response):
    """Add CORS headers to all responses"""
    # Obținem originea cererii
    origin = request.headers.get('Origin', '*')
    
    # Permitem explicit originea localhost:3000 pentru dezvoltare
    if origin in ['http://localhost:3000', 'http://127.0.0.1:3000', 'http://127.0.0.1:50002']:
        response.headers.add('Access-Control-Allow-Origin', origin)
    else:
        response.headers.add('Access-Control-Allow-Origin', '*')
        
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,X-CSRF-Token')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS,PATCH')
    response.headers.add('Access-Control-Max-Age', '3600')
    return response

def setup_cors_middleware(app):
    """Setup CORS middleware for Flask app"""
    
    @app.after_request
    def after_request(response):
        return add_cors_headers(response)
    
    @app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
    @app.route('/<path:path>', methods=['OPTIONS'])
    def options_handler(path):
        """Handle OPTIONS requests for CORS preflight"""
        response = jsonify({'status': 'ok'})
        return add_cors_headers(response)
