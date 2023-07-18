# Network-Clock (NC)

## Connexion

This code has been tested on Ubuntu. \
To start it, you need to open two terminals (on PowerShell), one for the server and one for the client.

### Server

``python3 .\main.py``

### Client

``telnet <ip> 1234``

## Packages

All of those packages are needed to run the code :
 - os (OS)
 - sys (System)
 - arrow (Date and time)
 - socket (Socket)
 - subprocess (Run commands)
 - select (for non-blocking sockets)
 - threading (for multi-threading)
 - json (JSON)
 - hashlib (Hashing)
 - prctl (Process control for Linux)

## Commands

### Server-side

 - v - to toggle verbose mode (less/more output)
 - c - to change server's time
 - q - to quit
 - t - to get the time
 - h - to get help

### Client-side

- c - to change the time format
- q - to quit
- t - to get the time
- h - to get help

## Reviews

### Fixes in 1.0

- [x] Removed outputs and logs in admin mode
- [x] Added capabilites with prctl
- [x] Removed datetime and replaced it with arrow (more efficient and secure : https://snyk.io/advisor/python/arrow)
- [x] Removed validate_time_format()
- [x] Fixed the decoding of inputs, 1024 bytes instead of 1
- [x] Time isn't send every second anymore but on request
- [x] Added administrative privileges in change_time()
- [x] Added full path and hash check when calling time_changer.py
- [x] Removed regexp in validate_format()
- [x] Removed get_hours_minutes_seconds() and get_day_month_year()
- [x] Removed send_message_to_clients() and print_message_to_clients()
- [x] Removed prompt_mode_selection() and starting both offline and online mode at the same time
- [x] Added config.json