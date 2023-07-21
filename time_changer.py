############## IMPORTS ##############

import ctypes  # C types (for system API)
import ctypes.util  # C types utilities
import sys  # System
import arrow  # Date and time
import prctl  # Process control

############## CONFIGURATION ##############

# Loading the system C libraries
libc = ctypes.CDLL(ctypes.util.find_library('c'))
libcso6 = ctypes.CDLL('libc.so.6')

# Constants
PR_SET_MM = 0x6  # prctl option for setting the process mm (memory management) flags
PR_SET_MM_EXE_FILE = 10  # prctl option for setting the process mm (memory management) flags to disable DEP
CLOCK_REALTIME = 0  # Clock ID for the system real time clock


############## FUNCTIONS ##############

class Timespec(ctypes.Structure):
    _fields_ = [
        ('tv_sec', ctypes.c_long),
        ('tv_nsec', ctypes.c_long)
    ]


# Change system time and date with the given parameters
def change_system_time(new_time):
    # Getting the clock_settime function from the C library
    settime = libc.clock_settime

    # Setting the return type of the function
    ts = Timespec()
    ts.tv_sec = int(new_time.timestamp())
    ts.tv_nsec = 0

    # Calling settime with the new time
    settime(CLOCK_REALTIME, ctypes.byref(ts))


# Secure the execution of the program by limiting the capabilities of the current process ID
def secure_execution():
    # Define the capabilities to be limited to CAP_SYS_TIME
    prctl.cap_effective.limit(prctl.CAP_SYS_TIME)
    prctl.cap_permitted.limit(prctl.CAP_SYS_TIME)

    # Enable DEP
    libcso6.prctl(PR_SET_MM, PR_SET_MM_EXE_FILE, 1, 0, 0)


if __name__ == '__main__':
    secure_execution()

    # Check if the number of arguments is correct
    if len(sys.argv) != 3:
        sys.exit(1)

    # Get date and time from arguments
    date_string, time_string = sys.argv[1].strip(), sys.argv[2].strip()

    # Check if the date and time are valid
    try:
        combined_datetime = arrow.get(f"{date_string} {time_string}", 'YYYY-MM-DD HH:mm:ss')
    except arrow.parser.ParserError:
        sys.exit(1)

    change_system_time(combined_datetime)
