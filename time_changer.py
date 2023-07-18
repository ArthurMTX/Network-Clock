############## IMPORTS ##############

import datetime  # Date and time
import os  # Operating system
import subprocess  # Run commands
import sys  # System
import prctl  # Process control


############## FUNCTIONS ##############

# Change system time and date with the given parameters
def change_system_time(new_date, new_time):
    try:
        # Reformat date and time (YYYY-MM-DD and HH:MM:SS)
        formatted_date = new_date.strftime('%Y-%m-%d')
        formatted_time = new_time.strftime('%H:%M:%S')

        # Execute command to change system time and date
        subprocess.run(["timedatectl", "set-time", formatted_date], capture_output=True)
        subprocess.run(["timedatectl", "set-time", formatted_time], capture_output=True)
    except subprocess.CalledProcessError:
        sys.exit(1)


# Secure the execution of the program by limiting the capabilities of the current process ID
def secure_execution():
    try:
        # Define the capabilities to be limited to CAP_SYS_TIME
        prctl.cap_effective.limit(prctl.CAP_SYS_TIME)
        prctl.cap_permitted.limit(prctl.CAP_SYS_TIME)

        # Check if the capabilities were limited
        capcheck = subprocess.run(["getpcaps", str(os.getpid())], capture_output=True, text=True)

        # If the capabilities were not limited, exit the program
        if "cap_sys_time" not in capcheck.stdout.lower():
            sys.exit(1)
    except Exception as e:
        sys.exit(1)


if __name__ == '__main__':
    # Check if the number of arguments is correct
    if len(sys.argv) != 3:
        sys.exit(1)

    # Get date and time from arguments
    date_string, time_string = sys.argv[1].strip(), sys.argv[2].strip()

    # Check if the date and time are valid
    try:
        date = datetime.datetime.strptime(date_string, '%Y-%m-%d')
        time = datetime.datetime.strptime(time_string, '%H:%M:%S')
    except ValueError:
        sys.exit(1)

    secure_execution()
    change_system_time(date, time)
