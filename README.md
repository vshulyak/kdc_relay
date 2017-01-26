# kdc_relay

Adapted script based on kdc_tunnel


## Remote (should be running already):

    python /share/kdc_relay.py remote 10088:host:88

## Local:

    ssh -fN -o ExitOnForwardFailure=yes  -L 10088:localhost:10088 user@host
    sudo python2.7 kdc_relay.py local 88:localhost:10088


See this for improvements:
https://gist.github.com/scy/6781836 (to run ssh tunnel from python script)
