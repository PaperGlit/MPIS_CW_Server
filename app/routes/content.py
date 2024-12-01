import os
from flask import Blueprint, request, jsonify, send_file
from app.models.database import get_connection
from app.services.file_handler import save_file


content_bp = Blueprint('content', __name__)

@content_bp.route('/upload', methods=['POST'])
def upload_audio():
    file = request.files.get('file')
    created_by = request.form.get('created_by')
    creator_type = request.form.get('creator_type')
    name = request.form.get('name')
    if not all([file, created_by, creator_type, name]):
        return jsonify({"error": "Missing required parameters"}), 400
    upload_dir = f"uploads/{created_by}/"
    file_path = save_file(file, upload_dir, name)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO content (name, created_by, creator_type, file_path) VALUES (%s, %s, %s, %s)",
        (name, created_by, creator_type, file_path)
    )
    conn.commit()
    return jsonify({"message": "File uploaded successfully", "file_path": file_path}), 201

@content_bp.route('/download/<int:content_id>', methods=['GET'])
def download_audio(content_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM content WHERE id = %s", (content_id,))
    result = cursor.fetchone()
    if result:
        file_path = result[0]
        if os.path.exists(file_path):
            return send_file(f"../{file_path}", as_attachment=True)
        else:
            return jsonify({"error": "Content not found"}), 404
    return jsonify({"error": "Content not found"}), 404

@content_bp.route("/refresh", methods=["GET"])
def get_all_content():
    conn = get_connection()
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