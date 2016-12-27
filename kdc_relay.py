"""
Adapted script from kdc_tunnel

local_udp_client -> local_wrap() -> ssh_tunnel -> remote_unwrap() -> remote_udp_host
"""
import argparse
import select
import socket
import sys


def local_wrap(local_port, tunnel_host, tunnel_port):
    """
    Wrap to tunnel
    """
    # Create UDP socket and listen for KDC requests.
    incoming = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    incoming.bind((tunnel_host, local_port))
    print((tunnel_host, local_port))

    # For each KDC request received, initiate new TCP connection, pass the
    # request, and send any data received back to the UDP socket.
    while True:
        data, addr = incoming.recvfrom(1500)
        msg = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        msg.connect((tunnel_host, tunnel_port))
        msg.send(data)
        print("sent data %d" % len(data))
        msg.shutdown(socket.SHUT_WR)
        reply = ''
        while True:
            xreply = msg.recv(1500)
            print("receive data %d" % len(xreply))
            if not xreply:
                break
            reply += xreply

        incoming.sendto(reply, addr)
        msg.close()


def remote_unwrap(local_port, remote_host, remote_port):
    """
    Unwrap on remote
    """

    # Create TCP socket and listen to tunneled requests, and UDP socket for
    # outbound requests.
    msg = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    incoming = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    incoming.bind(('127.0.0.1', local_port))
    incoming.listen(1)

    # For each request received, send a UDP message and wait for exactly
    # one reply message, and send that back to the client. Close the TCP
    # connection immediately after sending the message data.
    while True:
        conn, addr = incoming.accept()
        data = conn.recv(1500)
        print("receive data %d" % len(data))
        while True:
            msg.sendto(data, (remote_host, remote_port))
            print("sent data " + str((remote_host, remote_port)))
            r, w, e = select.select([msg], [], [], 1)
            if msg not in r:
                continue
            reply, addr = msg.recvfrom(1500)
            print("receive data")
            break

        conn.send(reply)
        conn.close()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='KDC relay')
    parser.add_argument('mode', metavar='mode', type=str,
                        help='mode to run', choices=['local', 'remote'])
    parser.add_argument('redirect', metavar='redirect', type=str,
                        help='redirect address triple')
    args = parser.parse_args()

    redirect = args.redirect.split(':')
    if len(redirect) != 3 or not redirect[0].isdigit() or not redirect[2].isdigit():
        print("Provide one argument in LOCAL-PORT:HOSTNAME:REMOTE-PORT format")
        sys.exit(1)

    if args.mode == 'local':
        local_wrap(int(redirect[0]), redirect[1], int(redirect[2]))
    elif args.mode == 'remote':
        remote_unwrap(int(redirect[0]), redirect[1], int(redirect[2]))
    else:
        print("not a valid mode")
        sys.exit(1)
