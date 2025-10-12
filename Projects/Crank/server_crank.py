from flask import Flask, request, Response, jsonify
import os
import subprocess
import platform
import shutil
import time
import uuid

app = Flask(__name__)

BASE_DIR = os.getcwd()
UPLOAD_FOLDER = os.path.join(BASE_DIR, "received")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

RACHET_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "rachet", "rachet", "rachet"))
COMPILER_FILE = os.path.join(RACHET_DIR, "compiler.py")
RESET_FILE = os.path.join(RACHET_DIR, "reset.py")
ISO_NAME = "main.iso"

# Store compilation jobs in memory
compilation_jobs = {}

def python_command():
    return "python3"

def windows_to_wsl_path(win_path):
    drive, path_rest = os.path.splitdrive(win_path)
    drive = drive.lower().replace(":", "")
    path_rest = path_rest.replace("\\", "/")
    return f"/mnt/{drive}{path_rest}"

def compile_in_wsl(rx_path):
    """Compile .rx file silently in WSL."""
    rx_wsl = windows_to_wsl_path(rx_path)
    compiler_wsl = windows_to_wsl_path(COMPILER_FILE)
    rx_dir_wsl = os.path.dirname(rx_wsl)
    cmd = f"cd {rx_dir_wsl} && python3 {compiler_wsl} {rx_wsl}"
    result = subprocess.run(["wsl", "bash", "-c", cmd], capture_output=True, text=True)
    return result

def run_reset():
    """Run reset.py silently after sending ISO."""
    if platform.system() == "Windows":
        reset_wsl = windows_to_wsl_path(RESET_FILE)
        reset_dir_wsl = windows_to_wsl_path(RACHET_DIR)
        cmd_str = f"cd {reset_dir_wsl} && python3 {reset_wsl}"
        subprocess.run(["wsl", "bash", "-c", cmd_str], capture_output=True, text=True)
    else:
        subprocess.run([python_command(), RESET_FILE],
                       cwd=RACHET_DIR, capture_output=True, text=True)

@app.route("/compile", methods=["POST"])
def compile_file():
    """Step 1: Upload and compile, return job ID"""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No selected file"}), 400

    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(temp_path)
    
    # Copy to Rachet directory
    dest_path = os.path.join(RACHET_DIR, file.filename)
    shutil.copy2(temp_path, RACHET_DIR)

    print(f"[{job_id}] Received {file.filename}, starting compilation...")

    # Compile silently
    try:
        if platform.system() == "Windows":
            result = compile_in_wsl(dest_path)
        else:
            result = subprocess.run([python_command(), COMPILER_FILE, dest_path],
                           cwd=RACHET_DIR, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[{job_id}] Compilation FAILED")
            compilation_jobs[job_id] = {
                "status": "failed",
                "error": "Compilation failed",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            return jsonify({
                "job_id": job_id,
                "status": "failed",
                "error": "Compilation failed",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
            
    except Exception as e:
        print(f"[{job_id}] Compilation ERROR: {e}")
        compilation_jobs[job_id] = {
            "status": "failed",
            "error": str(e)
        }
        return jsonify({"job_id": job_id, "status": "failed", "error": str(e)}), 500

    # Wait for ISO to be created
    iso_path = os.path.join(RACHET_DIR, ISO_NAME)
    for _ in range(20):
        if os.path.exists(iso_path):
            break
        time.sleep(0.5)
    else:
        print(f"[{job_id}] ISO not generated")
        compilation_jobs[job_id] = {
            "status": "failed",
            "error": "ISO not generated in time"
        }
        return jsonify({"job_id": job_id, "status": "failed", "error": "ISO not generated"}), 500

    # Clean up .rx files
    try:
        os.remove(temp_path)
        os.remove(dest_path)
    except Exception:
        pass

    # Store job info
    compilation_jobs[job_id] = {
        "status": "ready",
        "iso_path": iso_path,
        "iso_size": os.path.getsize(iso_path)
    }

    print(f"[{job_id}] Compilation SUCCESS - ISO ready ({compilation_jobs[job_id]['iso_size']} bytes)")

    return jsonify({
        "job_id": job_id,
        "status": "ready",
        "iso_size": compilation_jobs[job_id]['iso_size']
    }), 200

@app.route("/download/<job_id>", methods=["GET"])
def download_iso(job_id):
    """Step 2: Download the compiled ISO"""
    if job_id not in compilation_jobs:
        return jsonify({"error": "Job not found"}), 404
    
    job = compilation_jobs[job_id]
    
    if job["status"] != "ready":
        return jsonify({"error": "ISO not ready", "status": job["status"]}), 400
    
    iso_path = job["iso_path"]
    
    if not os.path.exists(iso_path):
        return jsonify({"error": "ISO file missing"}), 500

    print(f"[{job_id}] Sending ISO...")

    # Read ISO into memory
    with open(iso_path, "rb") as f:
        iso_data = f.read()

    # Clean up
    try:
        run_reset()
        os.remove(iso_path)
        del compilation_jobs[job_id]
        print(f"[{job_id}] Cleanup complete")
    except Exception as e:
        print(f"[{job_id}] Cleanup error: {e}")

    # Return PURE BINARY - no text, no mixing
    response = Response(iso_data, mimetype="application/octet-stream")
    response.headers["Content-Disposition"] = f"attachment; filename={ISO_NAME}"
    response.headers["Content-Length"] = str(len(iso_data))
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)