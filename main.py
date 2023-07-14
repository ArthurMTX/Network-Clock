import datetime
import msvcrt
import re
import socket
import subprocess
import time
import select
import threading
import sys

time_format = ''
port = 1234
server_socket = None
default_time_format = '%Y-%m-%d %H:%M:%S'
verbose_mode = True
welcome_message = 'Welcome to NC Time Server!\n\r'
ascii_art = (
    "ooooo      ooo   .oooooo.   \r\n"
    " `888b.     `8'  d8P'  `Y8b  \r\n"
    "  8 `88b.    8  888          \r\n"
    "  8   `88b.  8  888          \r\n"
    "  8     `88b.8  888          \r\n"
    "  8       `888  `88b    ooo  \r\n"
    " o8o        `8   `Y8bood8P   \r\n"
)
explanation_message = 'Enter a time format string. The following are the valid format strings:\n\r \
     Year: %Y (e.g. 2018)\n\r \
     Month: %m (e.g. 01)\n\r \
     Day: %d (e.g. 01)\n\r \
     Hour: %H (e.g. 01)\n\r \
     Minute: %M (e.g. 01)\n\r \
     Second: %S (e.g. 01)\n\r \
     Year: %y (e.g. 18)\n\r \
     Month: %b (e.g. Jan)\n\r \
     Month: %B (e.g. January)\n\r \
     Day: %a (e.g. Mon)\n\r \
     Day: %A (e.g. Monday)\n\r \
     AM/PM: %p (e.g. AM)\n\rEnter nothing to use the default time format ({})\n\r'.format(default_time_format)
help_message_client = 'Enter: \n\r \
     c - to change the time format\n\r \
     q - to disconnect\n\r \
     h - to get help\n\r'
help_message_server = 'Enter: \n\r \
     v - to toggle verbose mode\n\r \
     q - to quit\n\r \
     h - to get help\n\r'
messages = {
    'success': '\033[92m [✓] {}\033[0m',
    'error': '\033[91m [x] {}\033[0m',
    'info': '\033[94m [i] {}\033[0m',
    'warning': '\033[93m [!] {}\033[0m',
    'yellow': '\033[93m {}\033[0m',
    'red': '\033[91m {}\033[0m',
    'invalid_time_format': 'Invalid time format: {}',
    'invalid_action': 'Invalid action: {}, use h for help',
    'invalid_character': 'Non-utf-8 character received: {}',
    'error_while_handling_client': 'Error occurred while handling client connection: {}',
    'keyboard_interrupt': 'Keyboard interrupt received. Closing the server socket.',
    'server_socket_closed': 'Server socket closed. Exiting the program.',
    'no_time_format_provided': 'No time format provided, using default ({})',
    'current_time_sent': 'Current time sent to the client - ip: {} port: {} time: {}',
    'time_format_requested': 'Time format requested by the client: {}',
    'time_format_changed': 'Time format changed to: {}',
    'connection_established': 'Connection established with {}:{}',
    'new_time_format': 'New time format requested by the client: {}',
    'client_disconnected': 'Client {}:{} disconnected.',
    'help_sent': 'Help sent to the client: {}:{}',
    'current_time': 'Current time: {}',
    'server_listening': 'Server is listening on {}:{}',
    'cant_decode': 'Couldn\'t decode received data, is socket closed?',
    'verbose_enabled': 'Verbose mode enabled',
    'verbose_disabled': 'Verbose mode disabled',
    'server_socket_closing': 'Closing the server socket...',
    'invalid_mode_selection': 'Invalid mode selection: {}',
    'no_time_provided': 'No time provided, using current time ({})',
    'no_date_provided': 'No date provided, using current date ({})',
    'invalid_time': 'Invalid time: {}',
    'invalid_date': 'Invalid date: {}',
    'changing_time': 'Changing server\'s time to: {}',
}


def print_message(message_key, *args):
    message = messages.get(message_key)
    if message:
        print(message.format(*args))


def validate_time_format(format_string):
    valid_formats = [
        '%Y', '%m', '%d', '%H', '%M', '%S', '%y', '%b', '%B', '%a', '%A', '%p'
    ]
    for valid_format in valid_formats:
        if valid_format in format_string:
            return True
    return False


def get_current_time(format_string):
    current_time = datetime.datetime.now()
    return datetime.datetime.strftime(current_time, format_string)


class ClientHandler(threading.Thread):
    def __init__(self, client_socket, client_address, default_time_format):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.default_time_format = default_time_format
        self.time_format = default_time_format

    def run(self):
        self.handle_client_connection()

    def receive_data(self):
        received_data = ''
        char = ''
        while True:
            try:
                char = self.client_socket.recv(1).decode('utf-8')
            except OSError as e:
                if e.errno == 10038:
                    print_message('error', messages['cant_decode'])
                    break
                else:
                    error_msg = messages['invalid_character'].format(str(e))
                    print_message('error', error_msg)
                    self.client_socket.send(format('\r\n' + error_msg).encode('utf-8'))
                    self.client_socket.close()
            if char == '\n':
                break
            received_data += char

        return received_data

    def send_current_time(self, time_format):
        try:
            current_time = get_current_time(time_format)
            self.client_socket.send('{}\r\n'.format(current_time).encode('utf-8'))
            if verbose_mode:
                print_message('success', messages['current_time_sent'].format(*self.client_address, current_time))
        except OSError as e:
            if e.errno == 10038:
                print_message('error', messages['cant_decode'])
            else:
                raise e

    def handle_change_format(self):
        while True:
            self.client_socket.send(format('\r\n' + explanation_message).encode('utf-8'))
            new_time_format = self.receive_data()

            if new_time_format.strip() == '':
                new_time_format = self.default_time_format
                print_message('warning', messages['no_time_format_provided'].format(new_time_format))
                self.client_socket.send('{}\r\n'.format(messages['no_time_format_provided']
                                                        .format(new_time_format)).encode('utf-8'))

            if not validate_time_format(new_time_format):
                error_msg = messages['invalid_time_format'].format(new_time_format)
                print_message('error', error_msg)
                self.client_socket.send(format(error_msg + '\r\n').encode('utf-8'))
            else:
                self.time_format = new_time_format
                print_message('success', messages['new_time_format'].format(self.time_format))
                self.client_socket.send('{}\r\n'.format(messages['time_format_changed']
                                                        .format(self.time_format)).encode('utf-8'))
                break

    def handle_disconnect(self):
        self.client_socket.send(format('\r\n' + 'Goodbye!').encode('utf-8'))
        print_message('info', messages['client_disconnected'].format(*self.client_address))
        self.client_socket.close()

    def handle_help(self):
        self.client_socket.send(format('\r\n' + help_message_client).encode('utf-8'))
        print_message('success', messages['help_sent'].format(*self.client_address))

    def handle_client_connection(self):
        self.client_socket.send(format(explanation_message).encode('utf-8'))

        while True:
            time_format = self.receive_data()

            if time_format.strip() == '':
                time_format = self.default_time_format
                print_message('warning', messages['no_time_format_provided'].format(time_format))

            if not validate_time_format(time_format):
                while True:
                    error_msg = messages['invalid_time_format'].format(time_format)
                    print_message('error', error_msg)
                    self.client_socket.send(format('{}\r\n'.format(error_msg)).encode('utf-8'))

                    time_format = self.receive_data()

                    if time_format.strip() == '':
                        time_format = self.default_time_format
                        print_message('warning', messages['no_time_format_provided'].format(time_format))
                        break

                    if validate_time_format(time_format):
                        break
            else:
                self.send_current_time(time_format)
                print_message('success', messages['time_format_requested'].format(time_format))

            last_check_time = time.time()
            while True:
                current_time = time.time()
                if current_time - last_check_time >= 1:
                    last_check_time = current_time
                    self.send_current_time(self.time_format)

                try:
                    if select.select([self.client_socket], [], [], 0)[0]:
                        char = self.client_socket.recv(1).decode('utf-8')

                        actions = {
                            'c': self.handle_change_format,
                            'q': self.handle_disconnect,
                            'h': self.handle_help,
                            '\n': None
                        }

                        action_func = actions.get(char)
                        if action_func is not None:
                            action_func()
                            if char == 'q':
                                return
                        else:
                            error_msg = '\r\n' + messages['invalid_action'].format(char)
                            print_message('error', error_msg)
                            self.client_socket.send('{}\r\n'.format(error_msg).encode('utf-8'))
                except OSError as e:
                    if e.errno == 10038:
                        print_message('error', messages['cant_decode'])
                        return
                    else:
                        raise e
                except ValueError:
                    print_message('error', messages['cant_decode'])
                    return


def open_socket():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip_address = socket.gethostbyname(socket.gethostname())
    server_address = (ip_address, port)
    server_socket.bind(server_address)
    server_socket.listen(1)
    print_message('info', messages['current_time'].format(get_current_time(default_time_format)))
    print_message('info', messages['server_listening'].format(*server_address))

    try:
        while True:
            print_message('info', 'Waiting for a connection...')
            client_socket, client_address = server_socket.accept()
            print_message('success', messages['connection_established'].format(*client_address))

            try:
                client_handler = ClientHandler(client_socket, client_address, default_time_format)
                client_handler.start()
            except Exception as e:
                error_msg = messages['error_while_handling_client'].format(str(e))
                print_message('error', error_msg)

    except KeyboardInterrupt:
        print_message('info', messages['keyboard_interrupt'])
        server_socket.close()
    finally:
        print_message('info', messages['server_socket_closed'])
        server_socket.close()


def run_server():
    open_socket_thread = threading.Thread(target=open_socket)
    open_socket_thread.start()
    open_socket_thread.join()


def change_time(new_time):
    command = ['runas', '/user:Administrator', 'python', 'time_changer.py', new_time]

    try:
        subprocess.run(command, check=True)
        print_message('success', messages['time_changed'].format(new_time))
    except subprocess.CalledProcessError as e:
        print_message('error', str(e))
    except Exception as e:
        print_message('error', str(e))


def validate_time(new_time):
    # check if time is in format HH:MM:SS
    if not re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$', new_time):
        return False

    # check if time is valid
    try:
        datetime.datetime.strptime(new_time, '%H:%M:%S')
    except ValueError:
        return False

    return True


def validate_date(new_date):
    # check if date is in format DD/MM/YYYY
    if not re.match(r'^([0-2][0-9]|3[0-1])/(0[1-9]|1[0-2])/[0-9]{4}$', new_date):
        return False

    # check if date is valid
    try:
        datetime.datetime.strptime(new_date, '%d/%m/%Y')
    except ValueError:
        return False

    return True


def get_hours_minutes_seconds():
    current_time = datetime.datetime.now()
    return current_time.strftime('%H:%M:%S').format(current_time.hour, current_time.minute, current_time.second)


def get_day_month_year():
    current_time = datetime.datetime.now()
    return current_time.strftime('%d/%m/%Y').format(current_time.day, current_time.month, current_time.year)


def handle_server_commands():
    while True:
        try:
            if msvcrt.kbhit():
                command = msvcrt.getch().decode()

                if not command.isalpha():
                    continue

                if command == 'v':
                    global verbose_mode
                    verbose_mode = not verbose_mode
                    if verbose_mode:
                        print_message('info', messages['verbose_enabled'])
                    else:
                        print_message('info', messages['verbose_disabled'])
                elif command == 'q':
                    print_message('info', messages['server_socket_closing'])
                    server_socket.close()
                    sys.exit(0)
                elif command == 'c':
                    new_time = input("Enter new time (HH:MM:SS): ").strip()

                    if new_time == '':
                        new_time = get_hours_minutes_seconds()
                        print_message('warning', messages['no_time_provided'].format(new_time))
                    else:
                        if not validate_time(new_time):
                            print_message('error', messages['invalid_time'].format(new_time))
                            continue

                    new_date = input("Enter new date (DD/MM/YYYY): ").strip()

                    if new_date == '':
                        new_date = get_day_month_year()
                        print_message('warning', messages['no_date_provided'].format(new_date))
                    else:
                        if not validate_date(new_date):
                            print_message('error', messages['invalid_date'].format(new_date))
                            continue

                    new_time = '{} {}'.format(new_date, new_time)
                    print_message('info', messages['changing_time'].format(new_time))
                    change_time(new_time)

                elif command == 'h':
                    print_message('info', help_message_server)
                elif command == '\r':
                    pass
                else:
                    print_message('error', messages['invalid_action'].format(command))
        except ValueError:
            print_message('error', messages['invalid_character'].format(command))
            continue


def prompt_mode_selection():
    print(messages['yellow'].format(ascii_art))
    print(messages['yellow'].format(welcome_message))

    while True:
        print("Select a mode:")
        print("1. Offline (only local)")
        print("2. Online (open a socket)")

        mode = input("Enter mode number (1 or 2): ").strip()

        if mode == "1":
            print("Running in Offline mode")
            run_offline_mode()
            break
        elif mode == "2":
            print("Running in Online mode")
            run_online_mode()
            break
        else:
            print_message('error', messages['invalid_mode_selection'].format(mode))


def run_offline_mode():
    default_time_format = '%Y-%m-%d %H:%M:%S'
    while True:
        current_time = get_current_time(default_time_format)
        print_message('info', messages['current_time'].format(current_time))
        time.sleep(1)


def run_online_mode():
    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    handle_server_commands()

    server_thread.join()


if __name__ == '__main__':
    prompt_mode_selection()
