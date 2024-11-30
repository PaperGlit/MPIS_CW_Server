from werkzeug.security import generate_password_hash, check_password_hash
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64
from flask import Flask, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MySQL Configuration
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'secondpair'

mysql = MySQL(app)

# RSA Key Pair Generation
private_key = RSA.generate(2048)
public_key = private_key.publickey()
cipher = PKCS1_OAEP.new(private_key)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Routes
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    encrypted_username = data.get('username')
    password = data.get('password')

    if not encrypted_username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Hash password and store in the database
    hashed_password = generate_password_hash(password)

    # You can either get name from the request or set it to a default
    name = "test"  # You can customize this as needed or add it to the request

    # Save to database
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, username, password, email) VALUES (%s, %s, %s, %s)",
                   (name, encrypted_username, hashed_password, "test@example.com"))
    conn.commit()

    return jsonify({"message": "User registered successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    encrypted_username = data.get('username')
    password = data.get('password')

    if not encrypted_username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    # Decrypt the username before comparing
    decrypted_username = cipher.decrypt(base64.b64decode(encrypted_username)).decode()

    # Fetch user data from the database
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM users WHERE username = %s", (encrypted_username,))
    result = cursor.fetchone()

    if result:
        db_encrypted_username, db_hashed_password = result

        # Check if the decrypted username matches the stored encrypted username
        if db_encrypted_username == encrypted_username and check_password_hash(db_hashed_password, password):
            return jsonify({"message": "Login successful"}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    else:
        return jsonify({"error": "User not found"}), 404


@app.route('/get_public_key', methods=['GET'])
def get_public_key():
    # Provide the public key to the client
    return jsonify({"public_key": public_key.export_key().decode()}), 200

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    # Validate request parameters
    if 'file' not in request.files or 'created_by' not in request.form or 'creator_type' not in request.form or 'name' not in request.form:
        return jsonify({"error": "Missing required parameters"}), 400

    file = request.files['file']
    created_by = request.form['created_by']
    creator_type = request.form['creator_type']  # 'user' or 'worker'
    name = request.form['name']

    # Validate creator_type
    if creator_type not in ['user', 'worker']:
        return jsonify({"error": "Invalid creator_type"}), 400

    # Validate and save the file
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE id = %s", created_by)
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

    # Save metadata to the database
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO content (name, created_by, creator_type, file_path) VALUES (%s, %s, %s, %s)",
        (name, created_by, creator_type, file_path)
    )
    conn.commit()

    return jsonify({"message": "File uploaded successfully", "file_path": file_path}), 201


@app.route('/get_all_content', methods=['GET'])
def get_all_content():
    conn = mysql.connection
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_by, creator_type, file_path FROM content")
    results = cursor.fetchall()

    # Format results into a list of dictionaries
    content_list = []
    for row in results:
        content = {
            "id": row[0],
            "name": row[1],
            "created_by": row[2],
            "creator_type": row[3],
            "file_path": row[4]
        }
        content_list.append(content)

    return jsonify(content_list), 200


@app.route('/download_audio/<int:content_id>', methods=['GET'])
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
    # Enable HTTPS

    ssl_context = ('cert.pem', 'key.pem')
    app.run(debug=True, ssl_context=ssl_context)
