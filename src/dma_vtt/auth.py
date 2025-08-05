"""
Authentication and authorization module for the DMA VTT application.

This module provides functions for user authentication, password hashing,
JWT token generation and validation, and role-based access control.
"""

import datetime
import jwt
from functools import wraps
from flask import request, jsonify, current_app
from passlib.hash import argon2
from .database import User, db


def hash_password(password):
    """
    Hash a password using Argon2 with appropriate parameters.
    
    Args:
        password: The plaintext password to hash
        
    Returns:
        str: The hashed password
    """
    # Using Argon2 with recommended parameters
    return argon2.using(
        time_cost=3,  # Number of iterations
        memory_cost=65536,  # Memory usage in kibibytes
        parallelism=4,  # Number of parallel threads
        salt_len=16,  # Salt length in bytes
        hash_len=32  # Hash length in bytes
    ).hash(password)


def verify_password(password, password_hash):
    """
    Verify a password against a hash.
    
    Args:
        password: The plaintext password to verify
        password_hash: The hashed password to compare against
        
    Returns:
        bool: True if the password matches, False otherwise
    """
    return argon2.verify(password, password_hash)


def generate_jwt(user_id, role, expiry_hours=24):
    """
    Generate a JWT token for a user.
    
    Args:
        user_id: The user's ID
        role: The user's role ('admin' or 'player')
        expiry_hours: Token validity in hours (default: 24)
        
    Returns:
        str: The JWT token
    """
    payload = {
        'sub': user_id,
        'role': role,
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=expiry_hours)
    }
    
    return jwt.encode(
        payload,
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )


def decode_jwt(token):
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        dict: The decoded payload if valid
        
    Raises:
        jwt.InvalidTokenError: If the token is invalid
    """
    return jwt.decode(
        token,
        current_app.config['SECRET_KEY'],
        algorithms=['HS256']
    )


def get_token_from_request():
    """
    Extract the JWT token from the request headers.
    
    Returns:
        str: The JWT token if found, None otherwise
    """
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    return None


def login_required(f):
    """
    Decorator to require a valid JWT token for a route.
    
    Args:
        f: The function to decorate
        
    Returns:
        function: The decorated function
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return jsonify({'message': 'Authentication token is missing'}), 401
        
        try:
            payload = decode_jwt(token)
            request.user_id = payload['sub']
            request.user_role = payload['role']
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid authentication token'}), 401
            
        return f(*args, **kwargs)
    
    return decorated


def admin_required(f):
    """
    Decorator to require admin role for a route.
    
    Args:
        f: The function to decorate
        
    Returns:
        function: The decorated function
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return jsonify({'message': 'Authentication token is missing'}), 401
        
        try:
            payload = decode_jwt(token)
            if payload['role'] != 'admin':
                return jsonify({'message': 'Admin privileges required'}), 403
                
            request.user_id = payload['sub']
            request.user_role = payload['role']
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid authentication token'}), 401
            
        return f(*args, **kwargs)
    
    return decorated


def register_user(username, password, role='player', registered_by=None):
    """
    Register a new user.
    
    Args:
        username: The username for the new user
        password: The plaintext password for the new user
        role: The role for the new user ('admin' or 'player')
        registered_by: The ID of the admin who is registering this user
        
    Returns:
        User: The newly created user object
        
    Raises:
        ValueError: If the username already exists
    """
    # Check if username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        raise ValueError(f"Username '{username}' already exists")
    
    # Create new user
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        registered_by=registered_by
    )
    
    db.session.add(user)
    db.session.commit()
    
    return user


def authenticate_user(username, password):
    """
    Authenticate a user with username and password.
    
    Args:
        username: The username to authenticate
        password: The plaintext password to verify
        
    Returns:
        tuple: (User object, JWT token) if authentication succeeds, (None, None) otherwise
    """
    user = User.query.filter_by(username=username).first()
    
    if user and verify_password(password, user.password_hash):
        token = generate_jwt(user.id, user.role)
        return user, token
    
    return None, None