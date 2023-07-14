import subprocess


def change_system_time(new_date, new_time):
    # Command to change the system date and time using cmd.exe
    command = f'cmd.exe /c date {new_date} & time {new_time}'

    try:
        subprocess.run(command, check=True, shell=True)
        print("System date and time changed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while changing system date and time: {e}")
    except Exception as e:
        print(f"Error occurred: {e}")


# Main entry point
if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        print("Invalid arguments. Usage: python time_changer.py DD/MM/YYYY HH:MM:SS")
        sys.exit(1)

    new_date = sys.argv[1]
    new_time = sys.argv[2]
    change_system_time(new_date, new_time)