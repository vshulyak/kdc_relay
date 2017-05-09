# kdc_relay

A script to automate connections to Kerberos (KDC) from your local machine using SSH tunnel and UDP forwarding.

Basically, it enables you to use kinit and kerberized apps on your localhost in case your KDC policies do not
allow this. This could be useful for debugging of apps that use Kerberos.

Always consult your colleagues about the current policies! It might be the case that you breach them if you use
this approach.

Some ideas taken from:
* https://github.com/lat/ssh-fu/
* https://github.com/sshuttle/sshuttle

## Use Case

In many cases commands kinit/klist/etc. don't work on your local machine if your clusters' KDC is protected
from external connections. So pointing to it directly doesn't work. And since Kerberos uses UDP it's not easy
to forward it using SSH-tunnel. This script automates:

* SSH Tunnel creation
* UDP wrapping and unwrapping
* Process cleanup

## Prerequisites

* You need to set up KDC location in your realm to a port > 1024 so that the script doesn't require root permissions.
(you can do it in /etc/krb5.conf)
* Set up password-less login to a tunnel server

## Usage:

    ./kdc_relay.py auto <local_kerberos_port>:<ssh_username@ssh_host>:<port on ssh host>:<kdc address>

## Example

    ./kdc_relay.py auto 1088:vshulyak@our-internal-node-1.root.com:11088:kdc-server.root.com
