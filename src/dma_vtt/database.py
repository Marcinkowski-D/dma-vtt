"""
Database models for the DMA VTT application.

This module defines the SQLAlchemy models for the application's database schema,
including User, Scene, Layer, Token, Drawing, TextElement, DiceFormula, DiceLog,
Note, ValueField, PointTracker, TokenAsset, and TokenFolder.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class User(db.Model):
    """
    User model representing both GM and player accounts.
    
    Attributes:
        id: Primary key
        username: Unique username
        password_hash: Argon2 hashed password with salt
        role: Either 'admin' (GM) or 'player'
        registered_by: ID of the admin who created this user
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False, default='player')  # 'admin' or 'player'
    registered_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationships
    created_users = relationship('User', backref='creator', remote_side=[id])
    scenes = relationship('Scene', backref='owner', lazy=True)
    dice_formulas = relationship('DiceFormula', backref='owner', lazy=True)
    dice_logs = relationship('DiceLog', backref='user', lazy=True)
    notes = relationship('Note', backref='owner', lazy=True)
    point_trackers = relationship('PointTracker', backref='owner', lazy=True)


class Scene(db.Model):
    """
    Scene model representing a game scene with multiple layers.
    
    Attributes:
        id: Primary key
        name: Scene name
        thumbnail_path: Path to the scene thumbnail image
        active: Whether this scene is currently active
        owner_id: ID of the user (GM) who created this scene
        background_layer_id: ID of the background layer
        foreground_layer_id: ID of the foreground layer
    """
    __tablename__ = 'scenes'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    thumbnail_path = Column(String(255), nullable=True)
    active = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    background_layer_id = Column(Integer, ForeignKey('layers.id'), nullable=True)
    foreground_layer_id = Column(Integer, ForeignKey('layers.id'), nullable=True)
    
    # Relationships
    layers = relationship('Layer', backref='scene', lazy=True, 
                          foreign_keys='Layer.scene_id')
    background_layer = relationship('Layer', foreign_keys=[background_layer_id])
    foreground_layer = relationship('Layer', foreign_keys=[foreground_layer_id])


class Layer(db.Model):
    """
    Layer model representing a canvas layer within a scene.
    
    Attributes:
        id: Primary key
        scene_id: ID of the scene this layer belongs to
        name: Layer name
        order_index: Position in the layer stack (z-index)
        type: Layer type ('background', 'player', 'custom')
        visible: Whether this layer is visible
    """
    __tablename__ = 'layers'
    
    id = Column(Integer, primary_key=True)
    scene_id = Column(Integer, ForeignKey('scenes.id'), nullable=False)
    name = Column(String(50), nullable=False)
    order_index = Column(Integer, nullable=False)
    type = Column(String(20), nullable=False)  # 'background', 'player', 'custom'
    visible = Column(Boolean, default=True)
    
    # Relationships
    tokens = relationship('Token', backref='layer', lazy=True)
    drawings = relationship('Drawing', backref='layer', lazy=True)
    text_elements = relationship('TextElement', backref='layer', lazy=True)


class Token(db.Model):
    """
    Token model representing a movable game piece on a layer.
    
    Attributes:
        id: Primary key
        layer_id: ID of the layer this token belongs to
        image_path: Path to the token image
        x, y: Position coordinates
        scale: Size scaling factor
        rotation: Rotation angle in degrees
        z_index: Stacking order within the layer
        metadata: Additional token data (name, etc.)
    """
    __tablename__ = 'tokens'
    
    id = Column(Integer, primary_key=True)
    layer_id = Column(Integer, ForeignKey('layers.id'), nullable=False)
    image_path = Column(String(255), nullable=False)
    x = Column(Float, nullable=False, default=0)
    y = Column(Float, nullable=False, default=0)
    scale = Column(Float, nullable=False, default=1.0)
    rotation = Column(Float, nullable=False, default=0)
    z_index = Column(Integer, nullable=False, default=0)
    metadata = Column(JSON, nullable=True)


class Drawing(db.Model):
    """
    Drawing model representing a vector drawing on a layer.
    
    Attributes:
        id: Primary key
        layer_id: ID of the layer this drawing belongs to
        type: Drawing type ('free', 'line', 'rectangle', 'circle')
        points: JSON array of point coordinates
        color: Hex color code
        stroke_width: Line thickness
    """
    __tablename__ = 'drawings'
    
    id = Column(Integer, primary_key=True)
    layer_id = Column(Integer, ForeignKey('layers.id'), nullable=False)
    type = Column(String(20), nullable=False)  # 'free', 'line', 'rectangle', 'circle'
    points = Column(JSON, nullable=False)  # JSON array of points
    color = Column(String(20), nullable=False)
    stroke_width = Column(Float, nullable=False, default=1.0)


class TextElement(db.Model):
    """
    TextElement model representing text on a layer.
    
    Attributes:
        id: Primary key
        layer_id: ID of the layer this text belongs to
        x, y: Position coordinates
        text: The text content
        font_size: Text size in pixels
        color: Hex color code
        style: Text style ('normal', 'bold', 'italic', 'bold-italic')
    """
    __tablename__ = 'text_elements'
    
    id = Column(Integer, primary_key=True)
    layer_id = Column(Integer, ForeignKey('layers.id'), nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    font_size = Column(Integer, nullable=False, default=12)
    color = Column(String(20), nullable=False, default='#000000')
    style = Column(String(20), nullable=False, default='normal')  # 'normal', 'bold', 'italic', 'bold-italic'


class DiceFormula(db.Model):
    """
    DiceFormula model representing a saved dice roll formula.
    
    Attributes:
        id: Primary key
        owner_id: ID of the user who created this formula (NULL for global)
        name: Formula name
        formula: The dice formula string (e.g., "1d20+3")
    """
    __tablename__ = 'dice_formulas'
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # NULL for global formulas
    name = Column(String(50), nullable=False)
    formula = Column(String(100), nullable=False)


class DiceLog(db.Model):
    """
    DiceLog model representing a record of a dice roll.
    
    Attributes:
        id: Primary key
        user_id: ID of the user who rolled the dice
        character_name: Name of the character making the roll
        formula_id: ID of the formula used (optional)
        raw_formula: The raw formula string used
        raw_result: The raw dice roll result
        modified_result: The final result after modifiers
        timestamp: When the roll was made
    """
    __tablename__ = 'dice_logs'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    character_name = Column(String(50), nullable=True)
    formula_id = Column(Integer, ForeignKey('dice_formulas.id'), nullable=True)
    raw_formula = Column(String(100), nullable=False)
    raw_result = Column(String(255), nullable=False)
    modified_result = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    formula = relationship('DiceFormula', backref='logs', lazy=True)


class Note(db.Model):
    """
    Note model representing a player's note.
    
    Attributes:
        id: Primary key
        owner_id: ID of the user who owns this note
        title: Note title
        content: Note content in Markdown format
    """
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    
    # Relationships
    value_fields = relationship('ValueField', backref='note', lazy=True)


class ValueField(db.Model):
    """
    ValueField model representing a field within a note.
    
    Attributes:
        id: Primary key
        note_id: ID of the note this field belongs to
        title: Field title
        value: Field value (string or numeric)
        formula: Optional formula for calculated fields
    """
    __tablename__ = 'value_fields'
    
    id = Column(Integer, primary_key=True)
    note_id = Column(Integer, ForeignKey('notes.id'), nullable=False)
    title = Column(String(50), nullable=False)
    value = Column(String(255), nullable=True)
    formula = Column(String(255), nullable=True)


class PointTracker(db.Model):
    """
    PointTracker model representing a resource tracker (e.g., health, mana).
    
    Attributes:
        id: Primary key
        owner_id: ID of the user who owns this tracker
        title: Tracker title
        current: Current value
        maximum: Maximum value
    """
    __tablename__ = 'point_trackers'
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(50), nullable=False)
    current = Column(Integer, nullable=False, default=0)
    maximum = Column(Integer, nullable=False, default=0)


class TokenFolder(db.Model):
    """
    TokenFolder model representing a folder in the token library.
    
    Attributes:
        id: Primary key
        parent_id: ID of the parent folder (NULL for root folders)
        name: Folder name
    """
    __tablename__ = 'token_folders'
    
    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey('token_folders.id'), nullable=True)
    name = Column(String(50), nullable=False)
    
    # Relationships
    subfolders = relationship('TokenFolder', backref=db.backref('parent', remote_side=[id]))
    assets = relationship('TokenAsset', backref='folder', lazy=True)


class TokenAsset(db.Model):
    """
    TokenAsset model representing a token image in the library.
    
    Attributes:
        id: Primary key
        folder_id: ID of the folder this token belongs to
        name: Token name
        path: Path to the token image file
        width: Image width in pixels
        height: Image height in pixels
    """
    __tablename__ = 'token_assets'
    
    id = Column(Integer, primary_key=True)
    folder_id = Column(Integer, ForeignKey('token_folders.id'), nullable=False)
    name = Column(String(100), nullable=False)
    path = Column(String(255), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)