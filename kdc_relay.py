#!/usr/bin/env python

"""
A script to wrap Kerberos UDP connection through tunnel to a destination KDC.

Based on this project:
https://github.com/lat/ssh-fu/

local_udp_client -> local_wrap() -> ssh_tunnel -> remote_unwrap() -> remote_udp_host
"""
from __future__ import print_function

import argparse
import os
import re
import select
import socket
import signal
import sys
import subprocess
import threading
import uuid


SERVER_PROC_FAKE_SCRIPT_NAME = "ssh_cmd_proxy_executable_%s.py" % uuid.uuid4()
KDC_DEFAULT_PORT = 88  # this is usually the case for many configurations


def local_wrap(local_port, tunnel_host, tunnel_port):
    """
    Wrap to tunnel on localhost
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
    Unwrap on remote machine (to which we ssh)
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


def auto_local(local_port, tunnel_username, tunnel_host, tunnel_port, destination_host):
    """
    Create local and remote wrappers automatically by uploading this script to tunnel host.
    """
    # contents of this file are loaded
    content = None
    with open(__file__, 'rb') as f:
        content = f.read()

    # contents of the script which waits for python code from socket
    pyscript = r"""
                import sys, os;
                sys.stdin = os.fdopen(0, "rb");
                exec(compile(sys.stdin.read(%d), "%s", "exec"));
                """ % (len(content), SERVER_PROC_FAKE_SCRIPT_NAME)
    pyscript = re.sub(r'\s+', ' ', pyscript.strip())

    # python command to be run on tunnel host (tested on 2.7 on our servers, should be probably updated for py3)
    py_cmd = "'python' -c '{pyscript}' remote {tunnel_port}:{destination_host}:{destination_port}"

    ssh_cmd = ["ssh",
               "%s@%s" % (tunnel_username, tunnel_host),
               '-L%d:localhost:%d' % (tunnel_port, tunnel_port),
               "--",
               py_cmd.format(pyscript=pyscript,
                             tunnel_port=tunnel_port,
                             destination_host=destination_host,
                             destination_port=KDC_DEFAULT_PORT)]

    # register signal handles which initiate another ssh session to kill remote unwrap process
    for sig in signal.SIGINT, signal.SIGTERM, signal.SIGQUIT, signal.SIGHUP:
        signal.signal(sig, lambda *args: kill_ssh(tunnel_username, tunnel_host))

    (s1, s2) = socket.socketpair()

    subprocess.Popen(ssh_cmd, stdin=s1, stdout=s1,
                     close_fds=True)

    s1.close()
    s2.sendall(content)

    # start local proxy
    thread = threading.Thread(target=local_wrap, args=(local_port, "localhost", tunnel_port))
    thread.daemon = True
    thread.start()

    # start listening for response from subprocess
    while True:
        try:
            res = s2.recv(1).decode()
            if res:
                print(res, end='')
        finally:
            s2.close()


def kill_ssh(tunnel_username, tunnel_host):
    """
    Kill ssh remote process. It doesn't exit by itself, so here's the hack.
    Possibly some socket connection could be used to singal termination, but that would be to cumbersome.
    """

    kill_cmd = ["ssh",
                "%s@%s" % (tunnel_username, tunnel_host),
                "--",
                "kill $(pgrep -u $USER -f %s)" % SERVER_PROC_FAKE_SCRIPT_NAME]

    os.spawnvp(os.P_WAIT, kill_cmd[0], kill_cmd)
    sys.exit(0)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='KDC proxy')
    parser.add_argument('mode', metavar='mode', type=str,
                        help='mode to run', choices=['auto', 'local', 'remote'])
    parser.add_argument('redirect', metavar='redirect', type=str,
                        help='redirect address triple')
    args = parser.parse_args()

    # auto mode
    if args.mode == 'auto':
        redirect = args.redirect.split(':')
        if len(redirect) != 4 or not redirect[0].isdigit() or not redirect[2].isdigit():
            print("Provide one argument in LOCAL-PORT:TUNNEL_SSH:REMOTE-PORT:DESTINATION-KDC-HOST format")
            sys.exit(1)

        if len(redirect[1].split("@")) != 2:
            print("Provide a valid username@host pair for TUNNEL_SSH")
            sys.exit(1)

        tunnel_username, tunnel_host = redirect[1].split("@")

        auto_local(int(redirect[0]), tunnel_username, tunnel_host, int(redirect[2]), redirect[3])

    # semi-auto modes (also used from auto mode)
    else:
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
