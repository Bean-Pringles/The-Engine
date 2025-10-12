import sys
import os
import requests

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ALIASES_PATH = os.path.join(SCRIPT_DIR, "ailias.txt")

args = sys.argv

if len(args) <= 1:
    print("Example Commands:")
    print("    flywheel connect <ip address> <name>")
    print("    flywheel send <name> <file name>")
    print("    flywheel clear")
    sys.exit()

action = args[1]

# --- Utility functions ---
def ensure_file_exists():
    if not os.path.exists(ALIASES_PATH):
        with open(ALIASES_PATH, 'w', encoding='utf-8') as f:
            pass

def search_alias(alias_name):
    ensure_file_exists()
    with open(ALIASES_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if alias_name.strip() == line.strip():
            if i + 1 < len(lines):
                return lines[i + 1].strip()
            else:
                return None
    return None

def add_alias(ip, alias):
    ensure_file_exists()
    with open(ALIASES_PATH, "a", encoding='utf-8') as f:
        f.write(f"{alias}\n{ip}\n")

def clear_aliases():
    ensure_file_exists()
    open(ALIASES_PATH, "w", encoding='utf-8').close()
    print("Aliases cleared")

# --- Command handlers ---
if action == "connect":
    if len(args) < 4:
        print("Usage: flywheel connect <ip address> <name>")
        sys.exit(1)
    ip = args[2]
    alias = args[3]
    add_alias(ip, alias)
    print(f"Connected: added alias '{alias}' with IP {ip}")

elif action == "clear":
    clear_aliases()

elif action == "send":
    if len(args) < 4:
        print("Usage: flywheel send <name> <file>")
        sys.exit(1)

    alias = args[2]
    file_path = args[3]

    ip = search_alias(alias)
    if not ip:
        print(f"Alias '{alias}' not found.")
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"File '{file_path}' does not exist.")
        sys.exit(1)

    print(f"[*] Uploading {file_path} to {ip}...")

    try:
        # STEP 1: Upload and compile (returns JSON with job ID)
        with open(file_path, "rb") as f:
            compile_response = requests.post(
                f"http://{ip}:5050/compile", 
                files={"file": f},
                timeout=60
            )

        if compile_response.status_code != 200:
            # Compilation failed
            print("[!] Compilation failed:")
            try:
                error_info = compile_response.json()
                print(f"Error: {error_info.get('error', 'Unknown error')}")
                if 'stdout' in error_info:
                    print("\n--- Compiler stdout ---")
                    print(error_info['stdout'])
                if 'stderr' in error_info:
                    print("\n--- Compiler stderr ---")
                    print(error_info['stderr'])
            except Exception:
                print(compile_response.text)
            sys.exit(1)

        # Get job ID from JSON response
        job_info = compile_response.json()
        job_id = job_info["job_id"]
        iso_size = job_info.get("iso_size", 0)
        
        print(f"[+] Compilation successful!")
        print(f"[+] Job ID: {job_id}")
        print(f"[+] ISO size: {iso_size} bytes")
        print(f"[*] Downloading ISO...")

        # STEP 2: Download the ISO (pure binary, no text)
        download_response = requests.get(
            f"http://{ip}:5050/download/{job_id}",
            timeout=30
        )

        if download_response.status_code != 200:
            print("[!] Download failed:")
            try:
                print(download_response.json())
            except Exception:
                print(download_response.text)
            sys.exit(1)

        # Write pure binary ISO to file
        output_file = os.path.join(os.getcwd(), "main.iso")
        with open(output_file, "wb") as iso_out:
            iso_out.write(download_response.content)
        
        actual_size = len(download_response.content)
        print(f"\n[+] Compilation finished. main.iso saved at: {output_file}")
        print(f"[+] Downloaded size: {actual_size} bytes")
        
        # Verify size matches
        if iso_size > 0 and actual_size != iso_size:
            print(f"[!] WARNING: Size mismatch! Expected {iso_size}, got {actual_size}")
            print(f"[!] ISO may be corrupted!")
        else:
            print("[+] ISO integrity verified - ready to boot!")

    except requests.exceptions.Timeout:
        print("[!] Request timed out. Server may be slow or unresponsive.")
    except requests.exceptions.RequestException as e:
        print(f"[!] Failed to connect to server: {e}")

else:
    print(f"Unknown command '{action}'")