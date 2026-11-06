#!/usr/bin/env python3
"""LeoMux: Commander socket/queue/tmux brain, hardened for native swipe approvals.

NDJSON on IPv4 loopback only. Socket-only by design, UI is an independent client.
"""
import argparse
import hashlib
import hmac
import json
import os
import queue
import re
import secrets
import socket
import threading
import time
from collections import deque

import protocol
import risk
from runner import Shell
from security import load_secret, verify
from voice import Voice
from grok import Grok

ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,32}$')


class Client:
    def __init__(self, sock):
        self.sock, self.authed = sock, False
        self.lock, self.busy = threading.Lock(), threading.Lock()
        self.history = deque(maxlen=12)

    def send(self, msg):
        try:
            with self.lock:
                self.sock.sendall(protocol.encode(msg))
        except OSError:
            pass


class LeoServer:
    def __init__(self, home, port=8765, mock=False, timeout=60,
                 tmux_socket=None, max_runtime=900):
        self.home = os.path.abspath(os.path.expanduser(home))
        os.makedirs(self.home, mode=0o700, exist_ok=True)
        os.chmod(self.home, 0o700)
        self.port, self.timeout, self.max_runtime = port, timeout, max_runtime
        self.token = load_secret(self.home, 'token')
        self.approval_key = load_secret(self.home, 'approval-key')
        self.session_id = secrets.token_hex(16)  # invalidates signatures after restart
        self.shell = Shell(self.home, tmux_socket=tmux_socket)
        self.voice, self.grok = Voice(mock), Grok()
        self.clients, self.pending, self.used_ids = set(), {}, set()
        self.lock, self.runq = threading.RLock(), queue.Queue(maxsize=32)
        self.paused, self.running, self.epoch = False, None, 0
        self.shutdown = threading.Event()
        self.listener = None
        self.async_slots = threading.BoundedSemaphore(2)
        self.voice_lock = threading.Lock()
        self.audit_lock = threading.Lock()

    def audit(self, event, **data):
        # No commands/output/secrets on disk in audit; PTY transcript stays local.
        path = os.path.join(self.home, 'history.jsonl')
        with self.audit_lock:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, 'a') as f:
                f.write(json.dumps({'event': event, 'ts': time.time(), **data}) + '\n')

    def broadcast(self, msg):
        with self.lock:
            clients = list(self.clients)
        for c in clients:
            if c.authed:
                c.send(msg)

    def status(self):
        with self.lock:
            return {'type': 'status', 'state': 'paused' if self.paused else
                    ('running' if self.running else 'idle'), 'paused': self.paused,
                    'running': self.running, 'pending': sorted(self.pending),
                    'session': 'leo', 'session_id': self.session_id, 'version': protocol.VERSION}

    def propose(self, client, msg):
        cmd = msg.get('cmd')
        if not isinstance(cmd, str) or not cmd.strip() or len(cmd) > 16000 or '\x00' in cmd:
            return client.send({'type': 'error', 'msg': 'propose needs a command of 1..16000 characters'})
        rating = risk.risk_for(cmd)
        # HARD refusal, never an approvable critical proposal.
        if rating['level'] == 'critical':
            self.audit('refused', tags=rating['tags'])
            return client.send({'type': 'error', 'msg': 'Critical command refused outright', 'risk': rating})
        with self.lock:
            cid = msg.get('id', secrets.token_hex(8))
            if not isinstance(cid, str) or not ID_RE.fullmatch(cid) or cid in self.used_ids:
                return client.send({'type': 'error', 'msg': 'bad or duplicate id'})
            if self.paused:
                return client.send({'type': 'error', 'msg': 'paused: explicitly resume before proposing'})
            if len(self.pending) >= 16 or self.runq.full() or len(self.used_ids) >= 10000:
                return client.send({'type': 'error', 'msg': 'proposal capacity reached'})
            self.used_ids.add(cid)
            timeout = msg.get('timeout', self.timeout)
            if type(timeout) not in (int, float) or not 1 <= timeout <= 300:
                timeout = self.timeout
            p = {'type': 'proposed', 'id': cid, 'cmd': cmd,
                 'reason': str(msg.get('reason', ''))[:500], 'risk': rating, 'timeout': timeout,
                 'deadline': time.time() + timeout, 'nonce': secrets.token_hex(32),
                 'cmd_hash': hashlib.sha256(cmd.encode()).hexdigest(),
                 'session_id': self.session_id, 'epoch': self.epoch}
            self.pending[cid] = p
        self.audit('propose', id=cid, risk=rating['level'])
        self.broadcast(p)
        for alert in risk.command_alerts(cmd):
            self.broadcast({'type': 'alert', 'id': cid, **alert})
        return p

    def decide(self, client, msg):
        with self.lock:
            p = self.pending.get(msg.get('id'))
            if p is None:
                return client.send({'type': 'error', 'msg': 'unknown or already decided'})
            decision = msg.get('decision')
            if decision not in ('approve', 'deny'):
                return client.send({'type': 'error', 'msg': 'invalid decision'})
            if time.time() >= p['deadline']:
                self._pause('timeout', p['id'])
                return
            if decision == 'approve' and not verify(self.approval_key, self.session_id, p, msg):
                self.audit('invalid_signature', id=p['id'])
                return client.send({'type': 'error', 'msg': 'native swipe signature required'})
            if decision == 'deny':
                return self._pause('deny', p['id'])
            del self.pending[p['id']]
            self.runq.put_nowait(p)
            self.audit('decision', id=p['id'], decision='approve')
            self.broadcast({'type': 'decision', 'id': p['id'], 'decision': 'approve'})

    def _pause(self, decision='cancelled', selected=None):
        # Caller holds RLock. Epoch invalidates even already-dequeued work.
        self.paused = True
        self.epoch += 1
        for cid in list(self.pending):
            self.broadcast({'type': 'decision', 'id': cid,
                            'decision': decision if cid == selected else 'cancelled'})
        self.pending.clear()
        while True:
            try:
                p = self.runq.get_nowait()
                self.broadcast({'type': 'decision', 'id': p['id'], 'decision': 'cancelled'})
            except queue.Empty:
                break
        self.audit('pause', reason=decision)
        self.broadcast(self.status())

    def stop(self):
        with self.lock:
            self._pause('stopped')
            # Kill only our known tmux session, never processes by broad name.
            # Unlike pause, emergency stop sacrifices cwd/env to halt execution.
            try:
                if self.shell.alive():
                    self.shell._t('kill-session', '-t', self.shell.session)
            except OSError:
                pass
        self.broadcast({'type': 'alert', 'level': 'high',
                        'msg': 'Emergency stop: queue cleared, leo session stopped. Explicit resume required.'})

    def worker(self):
        while not self.shutdown.is_set():
            try:
                p = self.runq.get(timeout=.2)
            except queue.Empty:
                continue
            with self.lock:
                if self.paused or p['epoch'] != self.epoch:
                    self.broadcast({'type': 'decision', 'id': p['id'], 'decision': 'cancelled'})
                    continue
                # Defense-in-depth if a policy changed before execution.
                if risk.risk_for(p['cmd'])['level'] == 'critical':
                    self._pause('refused', p['id'])
                    continue
                self.running = p['id']
                # Ensure/create under lock so a concurrent stop cannot miss a
                # session between marking running and injecting the command.
                try:
                    self.shell.ensure()
                except Exception:
                    self.running = None
                    self._pause('runner-unavailable')
                    self.broadcast({'type': 'exit', 'id': p['id'], 'code': -1,
                                    'summary': 'tmux unavailable; nothing retried.'})
                    continue
            self.broadcast(self.status())
            tail = deque(maxlen=32)

            def output(text):
                tail.append(text[-4096:])
                for data in protocol.chunk_text(text):
                    self.broadcast({'type': 'output', 'id': p['id'], 'stream': 'pty', 'data': data})

            try:
                # epoch checked again inside runner before send-keys (stop race).
                code = self.shell.run(p['id'], p['cmd'], output, self.max_runtime,
                                      guard=lambda: not self.paused and p['epoch'] == self.epoch,
                                      gate=self.lock)
            except Exception:
                output('[leo] runner failed; check Termux tmux installation\n')
                code = -1
            with self.lock:
                self.running = None
                # Failure/cancel is final: no retry, no queued work left pending.
                if code != 0:
                    self._pause('failed')
            self.audit('exit', id=p['id'], code=code)
            self.broadcast({'type': 'exit', 'id': p['id'], 'code': code,
                            'summary': 'Command finished with exit %s.' % code})
            for alert in risk.output_alerts(''.join(tail)):
                self.broadcast({'type': 'alert', 'id': p['id'], **alert})
            self.broadcast(self.status())

    def tick(self):
        while not self.shutdown.wait(.1):
            with self.lock:
                expired = next((p for p in self.pending.values() if time.time() >= p['deadline']), None)
                if expired:
                    self._pause('timeout', expired['id'])

    def asynchronous(self, client, task):
        if not client.busy.acquire(blocking=False):
            return client.send({'type': 'error', 'msg': 'voice/chat request already in progress'})
        if not self.async_slots.acquire(blocking=False):
            client.busy.release()
            return client.send({'type': 'error', 'msg': 'voice/chat capacity reached'})

        def run():
            try:
                task()
            except Exception as e:
                # Never leak HTTP bodies, API keys, environment or subprocess stderr.
                if isinstance(e, ValueError):
                    message = str(e)[:300]
                else:
                    message = 'Voice/chat request failed. Check Termux configuration; nothing was retried.'
                client.send({'type': 'error', 'msg': message})
            finally:
                client.send({'type': 'voice', 'state': 'idle'})
                self.async_slots.release()
                client.busy.release()
        threading.Thread(target=run, daemon=True).start()

    def chat(self, client, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 8000:
            raise ValueError('chat needs 1..8000 characters')
        content, proposal = self.grok.reply(text, client.history)
        client.history.append({'role': 'user', 'content': text})
        client.history.append({'role': 'assistant', 'content': content})
        client.send({'type': 'chat', 'role': 'leo', 'text': content})
        if proposal:
            self.propose(client, proposal)
        if client.authed:
            with self.voice_lock:
                self.voice.speak(content)

    def dispatch(self, c, msg):
        t = msg['type']
        if t == 'propose':
            self.propose(c, msg)
        elif t == 'decision':
            self.decide(c, msg)
        elif t in ('pause', 'resume'):
            with self.lock:
                if t == 'pause':
                    self._pause()
                else:
                    self.paused = False
                    self.audit('resume')
                    self.broadcast(self.status())
        elif t == 'stop':
            self.stop()
        elif t == 'status':
            c.send(self.status())
            with self.lock:
                for p in self.pending.values():
                    c.send(p)
        elif t == 'ping':
            c.send({'type': 'pong'})
        elif t == 'chat':
            self.asynchronous(c, lambda: self.chat(c, msg.get('text')))
        elif t == 'voice.listen':
            def listen():
                c.send({'type': 'voice', 'state': 'listening'})
                with self.voice_lock:
                    text = self.voice.listen()
                c.send({'type': 'transcript', 'text': text})
                # Recognition is NEVER parsed as a command or approval.
                self.chat(c, text)
            self.asynchronous(c, listen)
        else:
            c.send({'type': 'error', 'msg': 'unknown message type'})

    def handle(self, conn):
        c, framer = Client(conn), protocol.Framer()
        conn.settimeout(5)
        with self.lock:
            self.clients.add(c)
        try:
            while not self.shutdown.is_set():
                try:
                    data = conn.recv(65536)
                except socket.timeout:
                    # Android recognizer can temporarily own the foreground while
                    # JS heartbeats pause. Keep only an active voice/chat request.
                    if c.authed and c.busy.locked():
                        continue
                    break
                if not data:
                    break
                for msg in framer.feed(data):
                    if not c.authed:
                        token = msg.get('token')
                        if (msg['type'] != 'hello' or not isinstance(token, str) or
                                not hmac.compare_digest(token.encode(), self.token.encode())):
                            c.send({'type': 'error', 'msg': 'auth failed'})
                            self.audit('auth_fail')
                            return
                        c.authed = True
                        conn.settimeout(10)  # bounded writes; client sends periodic ping
                        c.send({'type': 'hello', 'ok': True, 'version': protocol.VERSION,
                                'session': 'leo', 'session_id': self.session_id})
                    else:
                        self.dispatch(c, msg)
        except (OSError, protocol.ProtocolError, ValueError, TypeError, KeyError):
            c.send({'type': 'error', 'msg': 'invalid message or connection closed'})
        finally:
            c.authed = False
            with self.lock:
                self.clients.discard(c)
            conn.close()

    def serve(self, ready=None):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(('127.0.0.1', self.port))  # NOT configurable: never expose to LAN
        srv.listen(8)
        srv.settimeout(.2)
        self.listener, self.port = srv, srv.getsockname()[1]
        for target in (self.worker, self.tick):
            threading.Thread(target=target, daemon=True).start()
        if ready:
            ready.set()
        try:
            while not self.shutdown.is_set():
                try:
                    conn, _ = srv.accept()
                except socket.timeout:
                    continue
                with self.lock:
                    if len(self.clients) >= 8:
                        conn.close()
                        continue
                threading.Thread(target=self.handle, args=(conn,), daemon=True).start()
        finally:
            srv.close()

    def close(self):
        self.shutdown.set()
        with self.lock:
            clients = list(self.clients)
        for c in clients:
            try:
                c.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def main():
    os.umask(0o077)
    if hasattr(os, 'getuid') and os.getuid() == 0:
        raise SystemExit('Refusing to run as root. Use ordinary Termux only.')
    ap = argparse.ArgumentParser(description='LeoMux localhost server (UI and headless share this process)')
    ap.add_argument('--home', default=os.environ.get('LEO_HOME', os.path.expanduser('~/.leomux')))
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--headless', action='store_true', help='socket-only mode (also the default)')
    args = ap.parse_args()
    if not 1 <= args.timeout <= 300:
        ap.error('timeout must be 1..300 seconds')
    server = LeoServer(args.home, timeout=args.timeout)
    print('LeoMux listening on 127.0.0.1:8765. Pair locally with leo.py pair; no secrets logged.', flush=True)
    try:
        server.serve()
    except KeyboardInterrupt:
        server.stop()
        server.close()


if __name__ == '__main__':
    main()
