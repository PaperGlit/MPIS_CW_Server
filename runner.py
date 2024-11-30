from werkzeug.security import generate_password_hash, check_password_hash
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64
from flask import Flask, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
from flask_mysql_connector import MySQL

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DATABASE'] = 'secondpair'
mysql = MySQL(app)
private_key = RSA.generate(2048)
public_key = private_key.publickey()
cipher = PKCS1_OAEP.new(private_key)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    encrypted_username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    if not name or not encrypted_username or not password or not email:
        return jsonify({"error": "Username and password are required"}), 400
    decrypted_username = cipher.decrypt(base64.b64decode(encrypted_username)).decode()
    decrypted_password = cipher.decrypt(base64.b64decode(password)).decode()
    hashed_password = generate_password_hash(decrypted_password)
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, username, password, email) VALUES (%s, %s, %s, %s)",
                   (name, decrypted_username, hashed_password, email))
    conn.commit()
    cursor.close()
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    encrypted_username = data.get('username')
    encrypted_password = data.get('password')
    if not encrypted_username or not encrypted_password:
        return jsonify({"error": "Username and password are required"}), 400
    decrypted_username = cipher.decrypt(base64.b64decode(encrypted_username)).decode()
    decrypted_password = cipher.decrypt(base64.b64decode(encrypted_password)).decode()
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password FROM users WHERE username = %s", (decrypted_username,))
    result = cursor.fetchone()
    cursor.close()
    if result:
        id, username, db_hashed_password = result
        if username == decrypted_username and check_password_hash(db_hashed_password, decrypted_password):
            return jsonify({"message": "Login successful", "id": id}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    else:
        return jsonify({"error": "User not found"}), 404

@app.route('/get_public_key', methods=['GET'])
def get_public_key():
    return jsonify({"public_key": public_key.export_key().decode()}), 200

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files or 'created_by' not in request.form or 'creator_type' not in request.form or 'name' not in request.form:
        return jsonify({"error": "Missing required parameters"}), 400
    file = request.files['file']
    created_by = request.form['created_by']
    creator_type = request.form['creator_type']
    name = request.form['name']
    if creator_type not in ['user', 'worker']:
        return jsonify({"error": "Invalid creator_type"}), 400
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute(f"SELECT username FROM users WHERE id = %s", (created_by,))
    creator_id = cursor.fetchone()
    if creator_id:
        path = app.config['UPLOAD_FOLDER'] + created_by + "/"
        os.makedirs(path, exist_ok=True)
        filename = secure_filename(name + ".mp3")
        i = 1
        while True:
            if i > 100:
                return jsonify({"error": "Invalid name"}), 400
            if os.path.exists(os.path.join(path, filename)):
                filename = secure_filename(name) + f"({i}).mp3"
                i += 1
            else:
                file_path = os.path.join(path, filename)
                break
    else:
        return jsonify({"error": "User not found"}), 404
    file.save(file_path)
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO content (name, created_by, creator_type, file_path) VALUES (%s, %s, %s, %s)",
        (name, created_by, creator_type, file_path)
    )
    conn.commit()
    return jsonify({"message": "File uploaded successfully", "file_path": file_path}), 201

@app.route('/content', methods=['GET'])
def get_all_content():
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_by, creator_type, file_path FROM content")
    results = cursor.fetchall()
    content_list = []
    for row in results:
        cursor.execute(f"SELECT name FROM users WHERE id = {row[2]}")
        creator = cursor.fetchone()
        content = {
            "id": row[0],
            "name": row[1],
            "created_by": row[2],
            "creator": creator[0],
            "file_path": row[4]
        }
        content_list.append(content)
    return jsonify(content_list), 200

@app.route('/download/<int:content_id>', methods=['GET'])
def download_audio(content_id):
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM content WHERE id = %s", (content_id,))
    result = cursor.fetchone()
    if result:
        file_path = result[0]
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    else:
        return jsonify({"error": "Content not found"}), 404

if __name__ == '__main__':
    ssl_context = ('cert.pem', 'key.pem')
    app.run(debug=True, ssl_context=ssl_context)
