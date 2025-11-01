import os
import subprocess

base_dir = os.path.dirname(os.path.abspath(__file__))
toolbox_script = os.path.join(base_dir, "toolbox.exe")
bat_path = os.path.join(base_dir, "toolbox.bat")

# Create the launcher batch file
if os.path.exists(bat_path):
    print("[*] Did not create toolbox.bat, file already exists.")
else:
    try:
        with open(bat_path, "w") as f:
            f.write(f'@echo off\n"{toolbox_script}" %*\n')
        print(f"[+] Created launcher: {bat_path}")
    except Exception as e:
        print(f"[!] Failed to create launcher: {e}")

# Add base_dir to the user's PATH if not already there
try:
    # Get current PATH from user environment
    result = subprocess.run(
        ['powershell', '-Command', '[Environment]::GetEnvironmentVariable("Path","User")'],
        capture_output=True, text=True
    )
    current_path = result.stdout.strip()

    if base_dir not in current_path.split(';'):
        # Append our directory to the PATH
        new_path = current_path + (';' if current_path else '') + base_dir
        subprocess.run([
            'powershell', '-Command',
            f'[Environment]::SetEnvironmentVariable("Path", "{new_path}", "User")'
        ], check=True)

        print(f"[+] Added {base_dir} to the user PATH.")
        print("[*] You may need to restart your terminal or sign out/in for the change to take effect.")
    else:
        print("[*] Directory already in PATH.")

except Exception as e:
    print(f"[!] Failed to update PATH: {e}")