import ctypes
import sys
import datetime
import re

def change_system_time(new_date, new_time):
    if not new_date and not new_time or len(new_date) != 10 or len(new_time) != 8:
        print("Invalid arguments. Usage: python time_changer.py MM-DD-YYYY HH:MM:SS")
        sys.exit(1)

    regex = re.compile(r'^\d{2}-\d{2}-\d{4}$')
    if not regex.match(new_date):
        print("Invalid date format. Please use the format MM-DD-YYYY")
        sys.exit(1)

    regex = re.compile(r'^\d{2}:\d{2}:\d{2}$')
    if not regex.match(new_time):
        print("Invalid time format. Please use the format HH:MM:SS")
        sys.exit(1)

    # Vérifier le format de la date
    try:
        date = datetime.datetime.strptime(new_date, "%m-%d-%Y").date()
    except ValueError:
        print("Invalid date format. Please use the format MM-DD-YYYY")
        sys.exit(1)

    # Vérifier le format de l'heure
    try:
        time = datetime.datetime.strptime(new_time, "%H:%M:%S").time()
    except ValueError:
        print("Invalid time format. Please use the format HH:MM:SS")
        sys.exit(1)

    # Convertir la date et l'heure en structure SYSTEMTIME
    class SYSTEMTIME(ctypes.Structure):
        _fields_ = [
            ('wYear', ctypes.c_uint16),
            ('wMonth', ctypes.c_uint16),
            ('wDay', ctypes.c_uint16),
            ('wHour', ctypes.c_uint16),
            ('wMinute', ctypes.c_uint16),
            ('wSecond', ctypes.c_uint16),
            ('wMilliseconds', ctypes.c_uint16),
        ]

    system_time = SYSTEMTIME()
    system_time.wYear = date.year
    system_time.wMonth = date.month
    system_time.wDay = date.day
    system_time.wHour = time.hour
    system_time.wMinute = time.minute
    system_time.wSecond = time.second
    system_time.wMilliseconds = 0

    # Appeler la commande runas avec ShellExecuteW en tant qu'administrateur
    shell32 = ctypes.windll.shell32
    result = shell32.ShellExecuteW(None, "runas", "cmd.exe", "/c date {0} & time {1}"
                                   .format(new_date, new_time), None, 1)

    # Vérifier le résultat de l'appel à la commande runas
    if result <= 32:
        error_msg = f"Failed to execute the command as administrator: Error code {result}"
        print(error_msg)
        sys.exit(1)

    print("System date and time changed successfully.")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Invalid arguments. Usage: python time_changer.py MM-DD-YYYY HH:MM:SS")
        sys.exit(1)

    datetime_string = sys.argv[1]

    try:
        date, time = datetime_string.split(' ')
        change_system_time(date, time)
    except ValueError:
        print("Invalid datetime format. Please use the format MM-DD-YYYY HH:MM:SS")
        sys.exit(1)
