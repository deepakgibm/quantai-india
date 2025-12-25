
import os
import subprocess

def get_python_processes():
    print("Listing Python processes...")
    try:
        # Using wmic if available, or just tasklist
        output = subprocess.check_output('wmic process where "name=\'python.exe\'" get commandline,processid', shell=True).decode()
        print(output)
    except Exception as e:
        print(f"WMIC failed: {e}")
        try:
            output = subprocess.check_output('tasklist /V /FI "IMAGENAME eq python.exe"', shell=True).decode()
            print(output)
        except Exception as e2:
            print(f"Tasklist failed: {e2}")

if __name__ == "__main__":
    get_python_processes()
