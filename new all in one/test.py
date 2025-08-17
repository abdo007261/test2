import subprocess
import os

# List of commands you want to run
commands = [
    'python script1.py',
    'python script2.py',
    'python script3.py'
]

# Loop through each command and open in a new CMD window
for command in commands:
    subprocess.Popen(['start', 'cmd', '/K', command], shell=True)
