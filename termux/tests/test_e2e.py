"""Real loopback TCP + real tmux; Android voice mocked, API never called."""
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import protocol
from leo_server import LeoServer
from security import sign


@unittest.skipUnless(shutil.which('tmux'), 'tmux required')
class E2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='leomux-test-')
        self.tmux = 'leomux-test-' + os.path.basename(self.tmp.name)
        self.srv = LeoServer(self.tmp.name, port=0, mock=True, timeout=3,
                             tmux_socket=self.tmux, max_runtime=5)
        ready = threading.Event()
        self.thread = threading.Thread(target=self.srv.serve, args=(ready,), daemon=True)
        self.thread.start()
        self.assertTrue(ready.wait(3))
        self.connections = []
        self.c = self.connect()
        self.hello = self.until(self.c, lambda m: m['type'] == 'hello')[0]

    def tearDown(self):
        for c in self.connections:
            c[0].close()
        self.srv.close()
        self.thread.join(2)
        subprocess.run(['tmux', '-L', self.tmux, 'kill-server'], capture_output=True)
        self.tmp.cleanup()

    def connect(self, token=None, first=None):
        sock = socket.create_connection(('127.0.0.1', self.srv.port), timeout=1)
        c = [sock, protocol.Framer(), []]
        self.connections.append(c)
        self.send(c, first or {'type': 'hello', 'token': token if token is not None else self.srv.token})
        return c

    def send(self, c, msg):
        c[0].sendall(protocol.encode(msg))

    def until(self, c, predicate, timeout=8):
        deadline, seen = time.monotonic() + timeout, []
        while time.monotonic() < deadline:
            while c[2]:
                msg = c[2].pop(0)
                seen.append(msg)
                if predicate(msg):
                    return msg, seen
            try:
                data = c[0].recv(65536)
            except socket.timeout:
                self.send(c, {'type': 'ping'})
                continue
            if not data:
                break
            c[2].extend(c[1].feed(data))
        self.fail('Timed out, message types: ' + repr([m['type'] for m in seen]))

    def propose(self, cmd, cid=None, timeout=3):
        m = {'type': 'propose', 'cmd': cmd, 'timeout': timeout}
        if cid:
            m['id'] = cid
        self.send(self.c, m)
        return self.until(self.c, lambda m: m['type'] == 'proposed')[0]

    def approve(self, p):
        self.send(self.c, {'type': 'decision', 'id': p['id'], 'decision': 'approve',
                          'nonce': p['nonce'], 'session_id': self.srv.session_id,
                          'signature': sign(self.srv.approval_key, self.srv.session_id, p)})

    def run_cmd(self, cmd):
        p = self.propose(cmd)
        self.approve(p)
        ex, seen = self.until(self.c, lambda m: m['type'] == 'exit' and m['id'] == p['id'])
        return ex, ''.join(m['data'] for m in seen if m['type'] == 'output'), p

    def test_hello_first_wrong_token_disconnect_and_loopback(self):
        self.assertEqual(self.srv.listener.getsockname()[0], '127.0.0.1')
        self.assertEqual(self.hello['version'], 2)
        for c in (self.connect(token='wrong'), self.connect(first={'type': 'status'})):
            err, _ = self.until(c, lambda m: m['type'] == 'error')
            self.assertEqual(err['msg'], 'auth failed')
            self.assertEqual(c[0].recv(10), b'')

    def test_unsigned_and_wrong_nonce_approvals_cannot_execute(self):
        p = self.propose('echo approved')
        self.send(self.c, {'type': 'decision', 'id': p['id'], 'decision': 'approve'})
        err, _ = self.until(self.c, lambda m: m['type'] == 'error')
        self.assertIn('signature', err['msg'])
        self.assertIn(p['id'], self.srv.pending)
        self.send(self.c, {'type': 'decision', 'id': p['id'], 'decision': 'approve',
            'nonce': 'wrong', 'session_id': self.srv.session_id,
            'signature': sign(self.srv.approval_key, self.srv.session_id, p)})
        self.until(self.c, lambda m: m['type'] == 'error')
        self.assertIsNone(self.srv.running)
        self.approve(p)
        ex, seen = self.until(self.c, lambda m: m['type'] == 'exit')
        self.assertEqual(ex['code'], 0)
        self.assertIn('approved', ''.join(m.get('data', '') for m in seen))
        self.approve(p)
        self.until(self.c, lambda m: m['type'] == 'error')

    def test_cwd_env_multiline_exit_and_streaming(self):
        ex, _, _ = self.run_cmd('cd ' + self.tmp.name + '\nexport LEO_MUX_TEST=42')
        self.assertEqual(ex['code'], 0)
        ex, out, _ = self.run_cmd('pwd; echo var=$LEO_MUX_TEST; echo héllo')
        self.assertEqual(ex['code'], 0)
        self.assertIn(self.tmp.name, out)
        self.assertIn('var=42', out)
        self.assertIn('héllo', out)
        self.assertNotIn('\x1e', out)
        ex, out, _ = self.run_cmd('echo before\nfalse')
        self.assertEqual(ex['code'], 1)
        self.assertIn('before', out)
        self.assertTrue(self.srv.paused)

    def test_critical_proposals_never_enter_pending_or_tmux(self):
        for cmd in ('rm -rf ~/stuff', 'su -c id', 'dd if=x of=y', 'ls /data', 'cat /system/build.prop'):
            self.send(self.c, {'type': 'propose', 'cmd': cmd})
            err, _ = self.until(self.c, lambda m: m['type'] == 'error')
            self.assertIn('Critical', err['msg'])
        self.assertEqual(self.srv.pending, {})
        self.assertFalse(self.srv.shell.alive())

    def test_expiry_denial_cancel_queue_and_require_resume(self):
        p = self.propose('echo never', timeout=1)
        decision, _ = self.until(self.c, lambda m: m['type'] == 'decision')
        self.assertEqual(decision['decision'], 'timeout')
        self.assertTrue(self.srv.paused)
        self.assertFalse(self.srv.shell.alive())
        self.send(self.c, {'type': 'propose', 'cmd': 'pwd'})
        self.until(self.c, lambda m: m['type'] == 'error')
        self.send(self.c, {'type': 'resume'})
        self.until(self.c, lambda m: m['type'] == 'status' and not m['paused'])
        p = self.propose('echo denied')
        self.send(self.c, {'type': 'decision', 'id': p['id'], 'decision': 'deny'})
        self.until(self.c, lambda m: m['type'] == 'decision' and m['id'] == p['id'])
        self.assertTrue(self.srv.paused)
        self.assertEqual(self.srv.pending, {})
        self.assertTrue(self.srv.runq.empty())

    def test_stop_kills_only_leo_session_cancels_approved_queue(self):
        p = self.propose('echo started; sleep 20', timeout=3)
        self.approve(p)
        self.until(self.c, lambda m: m['type'] == 'output' and 'started' in m['data'])
        q = self.propose('echo should-not-run')
        self.approve(q)
        self.until(self.c, lambda m: m['type'] == 'decision' and m['id'] == q['id'])
        self.send(self.c, {'type': 'stop'})
        self.until(self.c, lambda m: m['type'] == 'exit' and m['id'] == p['id'])
        self.assertTrue(self.srv.paused)
        self.assertTrue(self.srv.runq.empty())
        self.assertFalse(self.srv.shell.alive())
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, 'cmds', q['id'] + '.sh')))

    def test_voice_transcript_is_chat_never_an_approval(self):
        with patch.object(self.srv.grok, 'reply', return_value=('I heard you.', None)) as reply:
            self.send(self.c, {'type': 'voice.listen'})
            transcript, _ = self.until(self.c, lambda m: m['type'] == 'transcript')
            self.assertEqual(transcript['text'], 'test voice transcript')
            self.until(self.c, lambda m: m['type'] == 'voice' and m['state'] == 'idle')
            reply.assert_called_once()
        self.assertEqual(self.srv.pending, {})
        self.assertFalse(self.srv.shell.alive())

    def test_model_tool_call_becomes_pending_not_execution(self):
        with patch.object(self.srv.grok, 'reply', return_value=('Please review.', {'cmd': 'pwd', 'reason': 'test'})):
            self.send(self.c, {'type': 'chat', 'text': 'Where are we?'})
            p, _ = self.until(self.c, lambda m: m['type'] == 'proposed')
            self.assertIn(p['id'], self.srv.pending)
            self.assertFalse(self.srv.shell.alive())
            self.until(self.c, lambda m: m['type'] == 'voice' and m['state'] == 'idle')
