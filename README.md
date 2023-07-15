# Network-Clock (NC)

## Connexion

This code has been tested on Windows 11. \
To start it, you need to open two terminals (on PowerShell), one for the server and one for the client.

### Server

``py .\main.py``

### Client

``telnet <ip> 1234``

## Packages

All of those packages are needed to run the code :
 - sys (system)
 - datetime (date)
 - msvcrt (keyboard)
 - re (regex)
 - socket (network)
 - subprocess (process)
 - time (time)
 - select (input/output)
 - threading (thread)
 - ctypes (windows api)

## Commands

### Server-side

 - v - to toggle verbose mode (less/more output)
 - c - to change server's time
 - q - to quit
 - m - to send message to all clients
 - h - to get help

### Client-side

- c - to change the time format
- q - to quit
- h - to get help