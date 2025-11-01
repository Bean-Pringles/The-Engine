import subprocess
import os
import sys

script_directory = os.path.dirname(os.path.abspath(__file__))

def run(path):
    full_path = os.path.join(script_directory, path)
    if not os.path.exists(full_path):
        print(f"[!] File not found: {full_path}")
        return

    print(f"[+] Running: {full_path}\n")
    
    # Start process
    process = subprocess.Popen(
        [sys.executable, full_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Print output in real time
    for line in process.stdout:
        print(line, end='')

    process.wait()
    if process.returncode != 0:
        print(f"[!] Script exited with code {process.returncode}\n")
    else:
        print(f"[+] Script completed successfully\n")

run(r"setup.py")
run(r"Nim++/setup.py")
run(r"Chassis/setup.py")
run(r"Crank/setup.py")
run(r"rachet/rachet/setup.py")
run(r"spoke/Spoke-Shell/setup.py")
run(r"Toolbox/setup.py")
