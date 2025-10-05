#!/usr/bin/env python
import sys
import os
import shutil
import subprocess

args = sys.argv
if len(args) < 2:
    print("Usage:\n  chassis <language> <new_project>\n  chassis git <project_dir>")
    sys.exit(1)

command = args[1].lower()

# Path to the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))

if command == "git":
    # --- Git command ---
    if len(args) < 3:
        print("Usage: chassis git <project_dir>")
        sys.exit(1)

    project_dir = os.path.join(os.getcwd(), args[2])
    if not os.path.isdir(project_dir):
        print(f"[!] Project directory does not exist: {project_dir}")
        sys.exit(1)

    try:
        subprocess.run(["git", "init"], cwd=project_dir, check=True)
        print(f"Git repository initialized in '{project_dir}'")
    except FileNotFoundError:
        print("[!] Git is not installed or not in PATH")
    except subprocess.CalledProcessError as e:
        print(f"[!] Error initializing git: {e}")

else:
    # --- plate copy command ---
    if len(args) < 3:
        print("Usage: chassis <language> <new_project>")
        sys.exit(1)

    language = args[1]
    new_project = args[2]

    source_dir = os.path.join(script_dir, language)
    dest_dir = os.path.join(os.getcwd(), new_project)

    try:
        shutil.copytree(source_dir, dest_dir)
        print(f"Boilerplate '{language}' copied to '{dest_dir}'")
    except FileExistsError:
        print(f"[!] Destination '{dest_dir}' already exists")
        sys.exit(1)
    except FileNotFoundError:
        print(f"[!] Boilerplate '{language}' does not exist in '{script_dir}'")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error copying boilerplate: {e}")
        sys.exit(1)
