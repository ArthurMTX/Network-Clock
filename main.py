############## IMPORTS ##############

import os  # OS
import sys  # System
import socket  # Socket
import subprocess  # Run commands
import select  # Select (for non-blocking sockets)
import threading  # Threading
import ctypes  # C types (for system API)
import ctypes.util  # C types utilities
import json  # JSON (for config file)
import hashlib  # Hashing
import prctl  # Process control
import arrow  # Date and time

############## CONFIGURATION ##############

path = os.path.dirname(os.path.abspath(__file__))
python_exe_path = sys.executable

time_changer_script_path = os.path.join(path, "time_changer.py")
config_file_path = os.path.join(path, "config.json")

# Check if the config file exists and is readable
if not os.path.isfile(config_file_path) or not os.access(config_file_path, os.R_OK):
    sys.exit(1)

# Check if the time_changer.py file exists and is readable
if not os.path.isfile(time_changer_script_path) or not os.access(time_changer_script_path, os.R_OK):
    sys.exit(1)

# Read the config file
config_file = open("config.json", "r")
config = json.load(config_file)

port = config["port"]  # Port
max_connections = config["max_connections"]  # Max connections (server)
default_time_format = config["default_time_format"]  # Default time format

# Hash value of the time_changer.py file (to check if it was modified)
time_changer_hash = "ec4c6a1b1f2469d400a0f44ed6d3ca7adb69302feb7710b238d86db3ab6730a2"

time_format = ''  # Time format
connected_clients = []  # Connected clients
server_socket = None  # Server socket
verbose_mode = True  # Verbose mode

# Loading the system C libraries
libc = ctypes.CDLL(ctypes.util.find_library('c'))
libcso6 = ctypes.CDLL('libc.so.6')

# Constants
PR_SET_MM = 0x6  # prctl option for setting the process mm flags
PR_SET_MM_EXE_FILE = 10  # prctl option for setting the process mm flags to disable DEP
CLOCK_REALTIME = 0  # Clock ID for the system real time clock

############## MESSAGES ##############

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
     Year: YYYY (e.g. 2018)\n\r \
     Month: MM (e.g. 01)\n\r \
     Day: DD (e.g. 01)\n\r \
     Hour: HH (e.g. 01)\n\r \
     Minute: mm (e.g. 01)\n\r \
     Second: ss (e.g. 01)\n\r \
     Year: YY (e.g. 18)\n\r \
     Month: MMM (e.g. Jan)\n\r \
     Month: MMMM (e.g. January)\n\r \
     Day: ddd (e.g. Mon)\n\r \
     Day: dddd (e.g. Monday)\n\r \
     AM/PM: a (e.g. AM)\n\rEnter nothing to use the default time format ({}) : '.format(default_time_format)
help_message_client = 'Enter: \n\r \
     c - to change the time format\n\r \
     q - to disconnect\n\r \
     t - to get current time\n\r \
     h - to get help\n\r'
help_message_server = 'Enter: \n\r \
     v - to toggle verbose mode (less/more output)\n\r \
     c - to change server\'s time\n\r \
     t - to get current time\n\r \
     q - to quit\n\r \
     h - to get help\n\r'
messages = {
    'success': '\033[92m [✓] {}\033[0m',
    'error': '\033[91m [x] {}\033[0m',
    'info': '\033[94m [i] {}\033[0m',
    'warning': '\033[93m [!] {}\033[0m',
    'chat': '\033[95m [c] {}\033[0m',
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
    'error_while_changing_time': 'Error occurred while changing server\'s time',
    'time_changed': 'Server\'s time changed to: {}',
    'time_not_changed': 'Server\'s time not changed',
    'time_change_canceled': 'Time change canceled',
    'confirm_time_change': 'Are you sure you want to change server\'s time to {}? (y/n)',
    'sending_message_to_clients': 'Sending message to all clients: {}',
    'error_sending_message_to_clients': 'Error occurred while sending message to clients: {}',
    'message_sent_to_clients': 'Message sent to all clients: {}',
    'no_clients_connected': 'No clients connected',
}


############## FUNCTIONS ##############

# Secure the execution of the program by limiting the capabilities of the current process ID
def secure_execution():
    try:
        # Define the capabilities to be limited to none
        prctl.cap_effective.limit()
        prctl.cap_permitted.limit()

        # Disable DEP
        libcso6.prctl(PR_SET_MM, PR_SET_MM_EXE_FILE, 1, 0, 0)

    except Exception as e:
        print(e)
        sys.exit(1)


# Print message with color and special symbols (if supported)
def print_message(message_key, *args):
    message = messages.get(message_key)
    if message:
        print(message.format(*args))


# Get current time in given format and return it
def get_current_time(format_string):
    current_time = arrow.now()
    return current_time.format(format_string)


# Client handler class, handles client connection and communication
class ClientHandler(threading.Thread):
    def __init__(self, client_socket, client_address, client_time_format):
        super().__init__()
        self.client_socket = client_socket  # client socket
        self.client_address = client_address  # client address
        self.time_format = client_time_format  # client current time format

    # Handle client connection
    def run(self):
        self.handle_client_connection()

    # Read data from client and return when newline is received
    def receive_data(self):
        try:
            received_data = self.client_socket.recv(1024).decode('utf-8').strip()
            return received_data
        except OSError as e:
            # Error 10038 - socket closed or disconnected
            if e.errno == 10038:
                print_message('error', messages['cant_decode'])
            else:
                raise e

    # Send time to client in given format (or default if not provided)
    def send_current_time(self):
        try:
            # Fetch current format
            current_time = get_current_time(self.time_format)

            # Send current time to client
            self.client_socket.send('\r\n{}\r\n'.format(current_time).encode('utf-8'))

            # Print message server-side if verbose mode enabled
            if verbose_mode:
                print_message('success', messages['current_time_sent'].format(*self.client_address, current_time))
        except OSError as e:
            # Error 10038 - socket closed or disconnected
            if e.errno == 10038:
                print_message('error', messages['cant_decode'])
            else:
                raise e

    # Handle change format action, receive new format from client and change it (if valid)
    def handle_change_format(self):
        # Send the explanation message to the client
        self.client_socket.send(format(explanation_message).encode('utf-8'))

        # Receive new time format from client
        new_time_format = self.receive_data()

        # If empty string received, use default time format
        if new_time_format.strip() == '':
            new_time_format = default_time_format
            print_message('warning', messages['no_time_format_provided'].format(new_time_format))
            self.client_socket.send('{}\r\n'.format(messages['no_time_format_provided']
                                                    .format(new_time_format)).encode('utf-8'))

        # Update the time format
        self.time_format = new_time_format

        # Print success message
        print_message('success', messages['new_time_format'].format(self.time_format))
        self.client_socket.send('{}\r\n'.format(messages['time_format_changed']
                                                .format(self.time_format)).encode('utf-8'))

    # Handle client disconnection, send goodbye message and close socket and print success message server-side
    def handle_disconnect(self):
        self.client_socket.send(format('\r\n' + 'Goodbye!' '\r\n').encode('utf-8'))
        connected_clients.remove(self.client_socket)
        print_message('info', messages['client_disconnected'].format(*self.client_address))
        self.client_socket.close()

    # Handle help action, send help message to client and print success message server-side
    def handle_help(self):
        self.client_socket.send(format('\r\n' + help_message_client).encode('utf-8'))
        print_message('success', messages['help_sent'].format(*self.client_address))

    # Handle first client connection, receive action from client and handle it
    def handle_client_connection(self):
        connected_clients.append(self.client_socket)
        # Send explanation message to client
        self.client_socket.send(format(explanation_message).encode('utf-8'))

        while True:
            # Receive initial time format from client
            received_format = self.receive_data()

            # If empty string received, use default time format and print warning message server-side
            if received_format.strip() == '':
                received_format = default_time_format
                print_message('warning', messages['no_time_format_provided'].format(default_time_format))

            self.time_format = received_format

            self.send_current_time()
            print_message('success', messages['time_format_requested'].format(self.time_format))

            # Read action from client and handle it
            while True:
                # Try to read action from client
                try:
                    # If action received, handle it
                    if select.select([self.client_socket], [], [], 0)[0]:
                        # Read one character from client
                        char = self.client_socket.recv(1024).decode('utf-8').strip()

                        # If command is enter or return, ignore it
                        if char == '\r' or char == '\n':
                            continue

                        # Existing commands
                        commands = {
                            'c': self.handle_change_format,
                            'q': self.handle_disconnect,
                            'h': self.handle_help,
                            't': self.send_current_time,
                        }

                        # Link between character and function
                        # If character is not in commands, send error message to client
                        # If character is in commands, execute the function
                        commands_func = commands.get(char)
                        if commands_func is not None:
                            commands_func()
                            if char == 'q':
                                return
                        else:
                            error_msg = ' : ' + messages['invalid_action'].format(char)
                            self.client_socket.send('{}\r\n'.format(error_msg).encode('utf-8'))
                except OSError as e:
                    # Error 10038 - socket closed or disconnected
                    if e.errno == 10038:
                        print_message('error', messages['cant_decode'])
                        return
                    else:
                        raise e
                except ValueError:
                    # If bytes cannot be decoded, send error message to client and close socket
                    # Mainly because not UTF-8 encoding
                    print_message('error', messages['cant_decode'])
                    return


# Open socket and listen for connections, handle each connection in a new thread
def open_socket():
    global server_socket
    global max_connections
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a TCP/IP socket
    ip_address = socket.gethostbyname(socket.gethostname())  # Get local machine name
    server_address = (ip_address, port)  # Bind the socket to the port
    server_socket.bind(server_address)  # Listen for incoming connections
    server_socket.listen(1)  # Wait for a connection
    print_message('info', messages['current_time'].format(get_current_time(default_time_format)))
    print_message('info', messages['server_listening'].format(*server_address))

    connection_count = 0  # Counter for accepted connections

    try:
        while True:
            print_message('info', 'Waiting for a connection...')
            if connection_count >= max_connections:
                print_message('info', 'Maximum connections reached. Not accepting new connections.')
                break

            # Accept incoming connection
            client_socket, client_address = server_socket.accept()
            connection_count += 1

            print_message('success', messages['connection_established'].format(*client_address))

            try:
                # Create a new thread for each client and handle it
                client_handler = ClientHandler(client_socket, client_address, default_time_format)
                client_handler.start()
            except Exception as e:
                error_msg = messages['error_while_handling_client'].format(str(e))
                print_message('error', error_msg)

    except KeyboardInterrupt:
        # If keyboard interrupt, close socket and exit
        print_message('info', messages['keyboard_interrupt'])
        server_socket.close()
        sys.exit(0)
    finally:
        # If any other error, close socket and exit
        print_message('info', messages['server_socket_closed'])
        server_socket.close()
        sys.exit(1)


# Run server, open socket and listen for connections
def run_server():
    open_socket_thread = threading.Thread(target=open_socket)
    open_socket_thread.start()
    open_socket_thread.join()


# Change time server-side, using time_changer.py
def change_time(new_time):
    try:
        # Calculate the hash of the time_changer.py file
        with open(time_changer_script_path, 'rb') as file:
            file_content = file.read()
            hash_value = hashlib.sha256(file_content).hexdigest()

        # Compare the hash of the time_changer.py file with the stored hash
        if hash_value == time_changer_hash:
            # Construct the command to execute time_changer.py
            command = 'sudo "{}" "{}" {}'.format(python_exe_path, time_changer_script_path, new_time)

            # Execute command
            subprocess.call(command, shell=True)

            success_msg = messages['time_changed'].format(new_time)
            print_message('success', success_msg)
        else:
            error_msg = messages['error_while_changing_time']
            print_message('error', error_msg)
    except Exception as e:
        error_msg = messages['error_while_changing_time']
        print_message('error', error_msg)
        print(e)


# Validate time format, using arrow
# Return True if valid, False otherwise
def validate_time(new_time):
    # Check if time is valid by trying to convert it to arrow
    try:
        arrow.get(new_time, 'HH:mm:ss')
    except arrow.parser.ParserError:
        return False

    return True


# Validate date format, using arrow
# Return True if valid, False otherwise
def validate_date(new_date):
    # Check if date is valid by trying to convert it to arrow
    try:
        arrow.get(new_date, 'YYYY-MM-DD')
    except arrow.parser.ParserError:
        return False

    return True


# Handle server commands
def handle_server_commands():
    # Commands functions
    commands = {
        'v': toggle_verbose_mode,
        'q': quit_server,
        'c': change_system_date_and_time,
        'h': print_help_message,
        't': print_time_to_server
    }

    while True:
        try:
            # If key pressed, get command and handle it
            command = input()  # Use input() instead of msvcrt.getch()

            # If command is empty, ignore it
            if command.strip() == '':
                continue

            # If command not in commands, print error message
            if command not in commands:
                print_message('error', messages['invalid_action'].format(command))
                continue

            command_handler = commands[command]
            command_handler()

        except ValueError:
            print_message('error', messages['invalid_character'].format(command))
            continue


# Toggle verbose mode on/off
def toggle_verbose_mode():
    global verbose_mode
    verbose_mode = not verbose_mode
    if verbose_mode:
        print_message('info', messages['verbose_enabled'])
    else:
        print_message('info', messages['verbose_disabled'])


# Quit server and close socket
def quit_server():
    print_message('info', messages['server_socket_closing'])
    server_socket.close()
    sys.exit(0)


# Change server date and time and validate it
def change_system_date_and_time():
    # Ask for new time
    new_time = input("Enter new time (HH:MM:SS) (leave blank to use current time and use c to cancel): ").strip()

    # If cancel, return
    if new_time == 'c':
        print_message('info', messages['time_change_canceled'])
        return

    # If no time provided, get current time and print warning message
    # If time provided, validate it
    if new_time == '':
        current_time = arrow.now()
        new_time = current_time.format('HH:mm:ss')
        print_message('warning', messages['no_time_provided'].format(new_time))
    else:
        if not validate_time(new_time):
            print_message('error', messages['invalid_time'].format(new_time))
            return

    # Ask for new date
    new_date = input("Enter new date (YYYY-MM-DD) (leave blank to use current date and use c to cancel): ").strip()

    # If cancel, return
    if new_date == 'c':
        print_message('info', messages['time_change_canceled'])
        return

    # If no date provided, get current date and print warning message
    # If date provided, validate it
    if new_date == '':
        current_date = arrow.now().format('YYYY-MM-DD')
        new_date = current_date
        print_message('warning', messages['no_date_provided'].format(new_date))
    else:
        if not validate_date(new_date):
            print_message('error', messages['invalid_date'].format(new_date))
            return

    # Combine date and time and print message
    new_time = '{} {}'.format(new_date, new_time)

    # Ask for confirmation
    confirmation = input(messages['confirm_time_change'].format(new_time)).strip()

    # If confirmation is not y, return
    if confirmation != 'y':
        print_message('info', messages['time_change_canceled'])
        return

    # User confirmed, change time
    print_message('info', messages['changing_time'].format(new_time))
    change_time(new_time)


# Print help message
def print_help_message():
    print_message('info', help_message_server)


# Print current time to server
def print_time_to_server():
    print_message('info', messages['current_time'].format(get_current_time(default_time_format)))


# Run server online mode (with socket), open a socket and listen for connections
def run_online_mode():
    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    handle_server_commands()

    server_thread.join()


# Main function, ask for mode and run it either offline or online
if __name__ == '__main__':
    secure_execution()

    print(messages['yellow'].format(ascii_art))
    print(messages['yellow'].format(welcome_message))

    run_online_mode()
