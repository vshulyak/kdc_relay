import socket
import sys


def main(local_port, remote_addr, remote_port):

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('0.0.0.0', local_port))
    except:
        print("Failded to bind on port")
        sys.exit(1)

    print('Listening\n')

    knownClient = None
    knownServer = (remote_addr, remote_port)

    while True:
        data, addr = s.recvfrom(1500)
        if knownClient is None:
            knownClient = addr
        if addr == knownClient:
            s.sendto(data, knownServer)
        else:
            s.sendto(data, knownClient)


if __name__ == '__main__':

    if len(sys.argv) != 2:
        print("Provide one argument in LOCAL-PORT:HOSTNAME:REMOTE-PORT format")
        sys.exit(1)

    redirect = sys.argv[1].split(':')
    if len(redirect) != 3 or not redirect[0].isdigit() or not redirect[2].isdigit():
        print("Provide one argument in LOCAL-PORT:HOSTNAME:REMOTE-PORT format")
        sys.exit(1)

    local_port, remote_addr, remote_port = int(redirect[0]), redirect[1], int(redirect[2])

    main(local_port, remote_addr, remote_port)
