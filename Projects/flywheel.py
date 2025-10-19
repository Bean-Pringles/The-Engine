#!/usr/bin/env python3
import sys
import os
import subprocess

# -----------------------------
# Helper to run gears.py commands
# -----------------------------
def gearsCmds(current_dir, cmd, args_full):
    target_script = os.path.join(current_dir, "rachet", "rachet", "gears.py")
    if not os.path.exists(target_script):
        print(f"[!] gears.py not found at {target_script}")
        sys.exit(1)
    # Prepend the command itself so gears.py sees it
    subprocess.run([sys.executable, "-u", target_script, cmd, *args_full])

# -----------------------------
# Helper to run a Python script
# -----------------------------
def runPythonScript(script_path, args_full):
    if not os.path.exists(script_path):
        print(f"[!] Target script not found: {script_path}")
        sys.exit(1)
    subprocess.run([sys.executable, "-u", script_path, *args_full])

# -----------------------------
# Helper to run an executable
# -----------------------------
def runExecutable(exe_path, args_full):
    if not os.path.exists(exe_path):
        print(f"[!] Executable not found: {exe_path}")
        sys.exit(1)
    subprocess.run([exe_path, *args_full])

# -----------------------------
# Main function
# -----------------------------
def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    if len(sys.argv) < 2:
        print("""
Flywheel commands:

    compile
    interpret
    compress
    uncompress
    transform
    fetch
    run
    edit
    record
    install <apps or axle>
    shell
    browser
    valve
    magnet 
    connect
    send   
    clear
    server
    man
              """)
        sys.exit(1)

    cmd = sys.argv[1]
    args_full = sys.argv[2:]

    # ----------------------------------------
    # Rachet commands
    # ----------------------------------------
    if cmd in ("compile", "compress", "uncompress", "transform", "fetch"):
        gearsCmds(current_dir, cmd, args_full)

    if cmd == "interpret":
        runPythonScript(os.path.join(current_dir, "rachet", "rachet", "rachet", "interpreter.py"), args_full)
    
    # ----------------------------------------
    # Crank commands
    # ----------------------------------------
    elif cmd in ("connect", "send", "clear"):
        target_script = os.path.join(current_dir, "Crank", "crank.py")
        if not os.path.exists(target_script):
            print(f"[!] crank.py not found at {target_script}")
            sys.exit(1)
        subprocess.run([sys.executable, "-u", target_script, cmd, *args_full])

    elif cmd == "server":
        runPythonScript(os.path.join(current_dir, "Crank", "crank_server.py"))

    # ----------------------------------------
    # Spoke commands
    # ----------------------------------------
    elif cmd == "run":
        runPythonScript(os.path.join(current_dir, "spoke", "Interpreter", "spoke.py"), args_full)

    elif cmd == "edit":
        runPythonScript(os.path.join(current_dir, "spoke", "Spoke-Shell", "textEditor.py"), args_full)

    elif cmd == "record":
        runPythonScript(os.path.join(current_dir, "spoke", "Spoke-Shell", "apps", "notes", "notes.py"), args_full)

    # ----------------------------------------
    # Install sub-commands
    # ----------------------------------------
    elif cmd == "install":
        if len(sys.argv) < 3:
            print("Usage: flywheel install <apps|axle> [args...]")
            sys.exit(1)

        subcmd = sys.argv[2]
        args_full = sys.argv[3:]

        if subcmd == "apps":
            args_full.insert(0, "install")
            runPythonScript(os.path.join(current_dir, "spoke", "Spoke-Shell", "shellCommands", "apps.py"), args_full)

        elif subcmd == "axle":
            runPythonScript(os.path.join(current_dir, "spoke", "Spoke-Shell", "shellCommands", "import.py"), args_full)

        else:
            print(f"[!] Unknown install sub-command: {subcmd}")

    # ----------------------------------------
    # Other commands
    # ----------------------------------------
    elif cmd == "man":
        runPythonScript(os.path.join(current_dir, "Framework", "framework.py"), args_full[1:])
    
    elif cmd == "shell":
        runPythonScript(os.path.join(current_dir, "spoke", "Spoke-Shell", "shell.py"), args_full)

    elif cmd == "browser":
        runPythonScript(os.path.join(current_dir, "spoke", "Spoke-Shell", "apps", "browser", "browser.py"), args_full)

    elif cmd == "valve":
        runPythonScript(os.path.join(current_dir, "spoke", "Spoke-Shell", "shellCommands", "git.py"), args_full)

    elif cmd == "magnet":
        runExecutable(os.path.join(current_dir, "rachet", "Magnet", "magnet.exe"), args_full)

    elif cmd == "n++":
        runExecutable(os.path.join(current_dir, "Nim++", "preprocessor.exe"), args_full)

    else:
        print(f"[!] Unknown command: {cmd}")

# -----------------------------
# Bootstrap
# -----------------------------
if __name__ == "__main__":
    main()
