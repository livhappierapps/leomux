#!/usr/bin/env python3
"""Local CLI: proposals/status/watch only. Approval remains in the native pane."""
import argparse
import json
import os
import socket
import sys
import time
import protocol
from security import load_secret


class Conn:
    def __init__(self, home, port=8765):
        with open(os.path.join(home, 'token')) as f:
            token = f.read().strip()
        self.s = socket.create_connection(('127.0.0.1', port), timeout=5)
        self.f, self.buf = protocol.Framer(), []
        self.send({'type': 'hello', 'token': token, 'client': 'leo-cli'})
        if not self.recv().get('ok'):
            raise RuntimeError('auth failed')
        self.s.settimeout(3)

    def send(self, msg):
        self.s.sendall(protocol.encode(msg))

    def recv(self):
        while not self.buf:
            try:
                data = self.s.recv(65536)
            except socket.timeout:
                self.send({'type': 'ping'})
                continue
            if not data:
                raise EOFError('server closed')
            self.buf += self.f.feed(data)
        return self.buf.pop(0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--home', default=os.environ.get('LEO_HOME', os.path.expanduser('~/.leomux')))
    sub = ap.add_subparsers(dest='op', required=True)
    p = sub.add_parser('propose')
    p.add_argument('cmd')
    p.add_argument('--reason', default='Manual proposal')
    d = sub.add_parser('deny')
    d.add_argument('id')
    for op in ('pair', 'pause', 'resume', 'stop', 'status', 'watch'):
        sub.add_parser(op)
    a = ap.parse_args()
    if a.op == 'pair':
        # Only explicitly invoked, locally, on the phone; never sent over socket.
        os.makedirs(a.home, mode=0o700, exist_ok=True)
        print('PRIVATE pairing values. Enter only in your own LeoMux app. Do not share.')
        print('Socket token:', load_secret(a.home, 'token'))
        print('Approval key:', load_secret(a.home, 'approval-key'))
        return
    c = Conn(a.home)
    try:
        if a.op == 'propose':
            c.send({'type': 'propose', 'cmd': a.cmd, 'reason': a.reason})
        elif a.op == 'deny':
            c.send({'type': 'decision', 'id': a.id, 'decision': 'deny'})
        elif a.op != 'watch':
            c.send({'type': a.op})
        while True:
            m = c.recv()
            if m['type'] == 'pong':
                continue
            print(json.dumps(m, ensure_ascii=False), flush=True)
            if a.op != 'watch' and m['type'] in ('error', 'status', 'decision', 'proposed', 'alert'):
                return
    finally:
        c.s.close()


if __name__ == '__main__':
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        pass
