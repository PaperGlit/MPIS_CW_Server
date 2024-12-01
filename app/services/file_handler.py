import os
from werkzeug.utils import secure_filename

def save_file(file, upload_dir, name):
    os.makedirs(upload_dir, exist_ok=True)
    filename = secure_filename(name + ".mp3")
    path = os.path.join(upload_dir, filename)
    i = 1
    while os.path.exists(path):
        filename = secure_filename(f"{name}({i}).mp3")
        path = os.path.join(upload_dir, filename)
        i += 1
    file.save(path)
    return path
