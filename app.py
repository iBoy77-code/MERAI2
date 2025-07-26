from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash
import os
import json
from werkzeug.utils import secure_filename
from datetime import datetime

# === Configuration ===
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'zip', 'rar', 'exe'}
METADATA_FILE = os.path.join(UPLOAD_FOLDER, 'metadata.json')
PENDING_REQUESTS_FILE = 'pending_requests.json'

app = Flask(__name__)
app.secret_key = 'merai-secret-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# === Utility Functions ===

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return []
    with open(METADATA_FILE, 'r') as f:
        return json.load(f)

def save_metadata(data):
    with open(METADATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_pending_requests():
    if not os.path.exists(PENDING_REQUESTS_FILE):
        return []
    with open(PENDING_REQUESTS_FILE, 'r') as f:
        return json.load(f)

def save_pending_requests(data):
    with open(PENDING_REQUESTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# === Routes ===

@app.route('/')
def home():
    metadata = load_metadata()
    return render_template('index.html', metadata=metadata)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    metadata = load_metadata()
    pending = load_pending_requests()

    if request.method == 'POST':
        file = request.files.get('file')
        name = request.form.get('name')
        description = request.form.get('description')
        paid = request.form.get('paid') == 'on'

        if not file or not allowed_file(file.filename):
            flash("Invalid file type or no file selected", "danger")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        metadata.append({
            "name": name,
            "description": description,
            "filename": filename,
            "paid": paid
        })
        save_metadata(metadata)

        flash(f"{name} uploaded successfully!", "success")
        return redirect(url_for('upload'))

    return render_template('upload.html', metadata=metadata, pending=pending)

@app.route('/download/<filename>')
def download_file(filename):
    metadata = load_metadata()
    item = next((m for m in metadata if m['filename'] == filename), None)

    if not item:
        flash("File not found.", "danger")
        return redirect(url_for('home'))

    if item.get('paid'):
        flash("Download not authorized. Please request and await approval.", "warning")
        return redirect(url_for('home'))

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/download_request/<filename>', methods=['POST'])
def download_request(filename):
    pending = load_pending_requests()
    if not any(req['filename'] == filename for req in pending):
        pending.append({
            "filename": filename,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_pending_requests(pending)
        flash(f"Download request for {filename} has been sent to admin.", "info")
    else:
        flash(f"Request for {filename} already exists.", "warning")
    return redirect(url_for('home'))

@app.route('/request_payment/<filename>', methods=['POST'])
def request_payment(filename):
    flash(f"Payment process initiated for {filename}.", "info")
    # Placeholder for real payment integration
    return redirect(url_for('home'))

@app.route('/approve_request/<filename>', methods=['POST'])
def approve_request(filename):
    metadata = load_metadata()
    pending = load_pending_requests()

    for item in metadata:
        if item['filename'] == filename:
            item['paid'] = False  # Once approved, switch to False to allow download
            break

    pending = [req for req in pending if req['filename'] != filename]
    save_metadata(metadata)
    save_pending_requests(pending)

    flash(f"{filename} approved and now downloadable.", "success")
    return redirect(url_for('upload'))

@app.route('/delete_metadata/<filename>', methods=['POST'])
def delete_metadata(filename):
    metadata = load_metadata()
    metadata = [item for item in metadata if item['filename'] != filename]
    save_metadata(metadata)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    flash(f"{filename} deleted.", "success")
    return redirect(url_for('upload'))

# === Main ===
if __name__ == "__main__":
    app.run(debug=True)
