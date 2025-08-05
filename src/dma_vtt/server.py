"""
Main server module for the DMA VTT application.

This module sets up the Flask application, configures the database connection,
defines REST endpoints, and implements WebSocket handlers for real-time synchronization.
"""

import os
import secrets
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS
from .database import db, User, Scene, Layer, Token, Drawing, TextElement
from .auth import login_required, admin_required, register_user, authenticate_user

# Create Flask application
app = Flask(__name__)
CORS(app)

# Configure application
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'postgresql://postgres:postgres@localhost/dma_vtt'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create database tables
@app.before_first_request
def create_tables():
    db.create_all()
    
    # Create admin user if none exists
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        try:
            register_user(
                username=os.environ.get('ADMIN_USERNAME', 'admin'),
                password=os.environ.get('ADMIN_PASSWORD', 'admin'),
                role='admin'
            )
            app.logger.info('Admin user created')
        except ValueError as e:
            app.logger.info(f'Admin user creation failed: {e}')

# Authentication routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400
    
    user, token = authenticate_user(username, password)
    
    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401
    
    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    })

@app.route('/api/auth/register', methods=['POST'])
@admin_required
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'player')
    
    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400
    
    if role not in ['admin', 'player']:
        return jsonify({'message': 'Role must be either "admin" or "player"'}), 400
    
    try:
        user = register_user(
            username=username,
            password=password,
            role=role,
            registered_by=request.user_id
        )
        
        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        }), 201
    except ValueError as e:
        return jsonify({'message': str(e)}), 400

# Scene routes
@app.route('/api/scenes', methods=['GET'])
@login_required
def get_scenes():
    # Admin can see all scenes, players can only see active scenes
    if request.user_role == 'admin':
        scenes = Scene.query.all()
    else:
        scenes = Scene.query.filter_by(active=True).all()
    
    return jsonify({
        'scenes': [{
            'id': scene.id,
            'name': scene.name,
            'thumbnail_path': scene.thumbnail_path,
            'active': scene.active
        } for scene in scenes]
    })

@app.route('/api/scenes', methods=['POST'])
@admin_required
def create_scene():
    data = request.get_json()
    name = data.get('name')
    
    if not name:
        return jsonify({'message': 'Scene name is required'}), 400
    
    scene = Scene(
        name=name,
        owner_id=request.user_id
    )
    
    # Create default layers
    background_layer = Layer(
        name='Background',
        order_index=0,
        type='background',
        visible=True
    )
    
    player_layer = Layer(
        name='Player',
        order_index=1,
        type='player',
        visible=True
    )
    
    foreground_layer = Layer(
        name='Foreground',
        order_index=2,
        type='custom',
        visible=True
    )
    
    scene.layers.append(background_layer)
    scene.layers.append(player_layer)
    scene.layers.append(foreground_layer)
    
    scene.background_layer = background_layer
    scene.foreground_layer = foreground_layer
    
    db.session.add(scene)
    db.session.commit()
    
    return jsonify({
        'message': 'Scene created successfully',
        'scene': {
            'id': scene.id,
            'name': scene.name,
            'thumbnail_path': scene.thumbnail_path,
            'active': scene.active
        }
    }), 201

@app.route('/api/scenes/<int:scene_id>', methods=['GET'])
@login_required
def get_scene(scene_id):
    scene = Scene.query.get_or_404(scene_id)
    
    # Players can only access active scenes
    if request.user_role != 'admin' and not scene.active:
        return jsonify({'message': 'Scene not found'}), 404
    
    layers = []
    for layer in scene.layers:
        layer_data = {
            'id': layer.id,
            'name': layer.name,
            'order_index': layer.order_index,
            'type': layer.type,
            'visible': layer.visible
        }
        
        # Include tokens, drawings, and text elements for each layer
        if layer.type == 'player' or request.user_role == 'admin':
            layer_data['tokens'] = [{
                'id': token.id,
                'image_path': token.image_path,
                'x': token.x,
                'y': token.y,
                'scale': token.scale,
                'rotation': token.rotation,
                'z_index': token.z_index,
                'metadata': token.metadata
            } for token in layer.tokens]
            
            layer_data['drawings'] = [{
                'id': drawing.id,
                'type': drawing.type,
                'points': drawing.points,
                'color': drawing.color,
                'stroke_width': drawing.stroke_width
            } for drawing in layer.drawings]
            
            layer_data['text_elements'] = [{
                'id': text.id,
                'x': text.x,
                'y': text.y,
                'text': text.text,
                'font_size': text.font_size,
                'color': text.color,
                'style': text.style
            } for text in layer.text_elements]
        
        layers.append(layer_data)
    
    return jsonify({
        'scene': {
            'id': scene.id,
            'name': scene.name,
            'thumbnail_path': scene.thumbnail_path,
            'active': scene.active,
            'layers': layers
        }
    })

@app.route('/api/scenes/<int:scene_id>/activate', methods=['POST'])
@admin_required
def activate_scene(scene_id):
    scene = Scene.query.get_or_404(scene_id)
    
    # Deactivate all scenes
    Scene.query.update({'active': False})
    
    # Activate the selected scene
    scene.active = True
    db.session.commit()
    
    # Notify all clients about the scene change
    socketio.emit('scene_activated', {
        'scene_id': scene.id,
        'name': scene.name
    })
    
    return jsonify({
        'message': 'Scene activated successfully',
        'scene': {
            'id': scene.id,
            'name': scene.name,
            'active': True
        }
    })

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    # Authentication would be handled here in a production environment
    # using the JWT token from the request
    pass

@socketio.on('disconnect')
def handle_disconnect():
    pass

@socketio.on('token_moved')
def handle_token_moved(data):
    token_id = data.get('token_id')
    x = data.get('x')
    y = data.get('y')
    rotation = data.get('rotation')
    scale = data.get('scale')
    
    token = Token.query.get(token_id)
    if token:
        token.x = x
        token.y = y
        if rotation is not None:
            token.rotation = rotation
        if scale is not None:
            token.scale = scale
        
        db.session.commit()
        
        # Broadcast the token movement to all clients except the sender
        socketio.emit('token_moved', data, skip_sid=request.sid)

@socketio.on('drawing_created')
def handle_drawing_created(data):
    layer_id = data.get('layer_id')
    drawing_type = data.get('type')
    points = data.get('points')
    color = data.get('color')
    stroke_width = data.get('stroke_width')
    
    drawing = Drawing(
        layer_id=layer_id,
        type=drawing_type,
        points=points,
        color=color,
        stroke_width=stroke_width
    )
    
    db.session.add(drawing)
    db.session.commit()
    
    # Include the new drawing ID in the response
    data['id'] = drawing.id
    
    # Broadcast the new drawing to all clients except the sender
    socketio.emit('drawing_created', data, skip_sid=request.sid)

@socketio.on('text_created')
def handle_text_created(data):
    layer_id = data.get('layer_id')
    x = data.get('x')
    y = data.get('y')
    text = data.get('text')
    font_size = data.get('font_size')
    color = data.get('color')
    style = data.get('style')
    
    text_element = TextElement(
        layer_id=layer_id,
        x=x,
        y=y,
        text=text,
        font_size=font_size,
        color=color,
        style=style
    )
    
    db.session.add(text_element)
    db.session.commit()
    
    # Include the new text element ID in the response
    data['id'] = text_element.id
    
    # Broadcast the new text element to all clients except the sender
    socketio.emit('text_created', data, skip_sid=request.sid)

# Main entry point
def main():
    """Run the Flask application with SocketIO support."""
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()