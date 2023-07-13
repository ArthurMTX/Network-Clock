import datetime
import socket
import time
import select
import threading
from pyreadline3 import Readline

readline = Readline()
time_format = ''
port = 1234
server_socket = None

messages = {
    'success': '\033[92m [✓] {}\033[0m',
    'error': '\033[91m [x] {}\033[0m',
    'info': '\033[94m [i] {}\033[0m',
    'warning': '\033[93m [!] {}\033[0m',
    'invalid_time_format': 'Invalid time format: {}',
    'invalid_action': 'Invalid action: {}, use h for help',
    'invalid_character': 'Non-utf-8 character received: {}',
    'error_while_handling_client': 'Error occurred while handling client connection: {}',
    'keyboard_interrupt': 'Keyboard interrupt received. Closing the server socket.',
    'server_socket_closed': 'Server socket closed. Exiting the program.',
    'no_time_format_provided': 'No time format provided, using default ({})',
    'current_time_sent': 'Current time sent to the client - ip: {} port: {} time: {}',
    'time_format_requested': 'Time format requested by the client: {}',
    'connection_established': 'Connection established with {}:{}',
    'new_time_format': 'New time format requested by the client: {}',
    'client_disconnected': 'Client {}:{} disconnected.',
    'help_sent': 'Help sent to the client: {}:{}',
    'current_time': 'Current time: {}',
    'server_listening': 'Server is listening on {}:{}',
    'cant_decode': 'Couldn\'t decode received data, is socket closed?'
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
    def __init__(self, client_socket, client_address, time_format):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.time_format = time_format
        self.default_time_format = default_time_format

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
            print_message('success', messages['current_time_sent'].format(*self.client_address, current_time))
        except OSError as e:
            if e.errno == 10038:
                print_message('error', messages['cant_decode'])
            else:
                raise e

    def handle_change_format(self):
        self.client_socket.send(format('\r\n' + explanation_message).encode('utf-8'))
        new_time_format = self.receive_data()

        while True:
            if new_time_format.strip() == '':
                new_time_format = self.default_time_format
                print_message('warning', messages['no_time_format_provided'].format(new_time_format))

            if not validate_time_format(new_time_format):
                error_msg = messages['invalid_time_format'].format(new_time_format)
                print_message('error', error_msg)
                self.client_socket.send(format(error_msg + '\r\n').encode('utf-8'))
                new_time_format = self.receive_data()
            else:
                self.time_format = new_time_format
                print_message('success', messages['new_time_format'].format(self.time_format))
                break

    def handle_disconnect(self):
        self.client_socket.send(format('\r\n' + 'Goodbye!').encode('utf-8'))
        print_message('info', messages['client_disconnected'].format(*self.client_address))
        self.client_socket.close()

    def handle_help(self):
        self.client_socket.send(format('\r\n' + help_message).encode('utf-8'))
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
                            self.client_socket.send(format(error_msg).encode('utf-8'))
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


def send_current_time_loop():
    while True:
        if server_socket is None:
            current_time = get_current_time(default_time_format)
            print_message('info', messages['current_time'].format(current_time))
        time.sleep(1)


def run_server(default_time_format):
    mode = get_server_mode()
    if mode == 'online':
        open_socket_thread = threading.Thread(target=open_socket)
        open_socket_thread.start()

    send_time_thread = threading.Thread(target=send_current_time_loop)
    send_time_thread.start()

    if mode == 'online':
        open_socket_thread.join()

    send_time_thread.join()


def get_server_mode():
    while True:
        mode = input("Select server mode (online/offline): ").lower()
        if mode in ['online', 'offline']:
            return mode
        else:
            print("Invalid server mode. Please choose 'online' or 'offline'.")


if __name__ == '__main__':
    default_time_format = '%Y-%m-%d %H:%M:%S'
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
    help_message = 'Enter: \n\r \
         c - to change the time format\n\r \
         q - to disconnect\n\r \
         h - to get help\n\r'

    run_server(default_time_format)