from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.database import get_connection
from app.services.crypto import get_public_key, decrypt_data

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/get_public_key', methods=['GET'])
def public_key():
    return jsonify({"public_key": get_public_key()}), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    encrypted_username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if not all([name, encrypted_username, password, email]):
        return jsonify({"error": "All fields are required"}), 400
    decrypted_username = decrypt_data(encrypted_username)
    decrypted_password = decrypt_data(password)
    hashed_password = generate_password_hash(decrypted_password)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, username, password, email) VALUES (%s, %s, %s, %s)",
        (name, decrypted_username, hashed_password, email)
    )
    conn.commit()
    cursor.close()
    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    encrypted_username = data.get('username')
    encrypted_password = data.get('password')
    if not all([encrypted_username, encrypted_password]):
        return jsonify({"error": "Username and password are required"}), 400
    decrypted_username = decrypt_data(encrypted_username)
    decrypted_password = decrypt_data(encrypted_password)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, password FROM users WHERE username = %s",
        (decrypted_username,)
    )
    user = cursor.fetchone()
    cursor.close()
    if user and check_password_hash(user[2], decrypted_password):
        return jsonify({"message": "Login successful", "id": user[0]}), 200
    return jsonify({"error": "Invalid credentials"}), 401
