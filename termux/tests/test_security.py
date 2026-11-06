import hashlib
import os
import sys
import tempfile
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from security import load_secret, sign, verify, approval_payload
import risk
import protocol


class Security(unittest.TestCase):
    def setUp(self):
        self.key = '01' * 32
        self.session = '02' * 16
        self.p = {'id': 'test', 'nonce': '03' * 32,
                  'cmd_hash': hashlib.sha256(b'pwd').hexdigest()}
        self.msg = {'nonce': self.p['nonce'], 'session_id': self.session,
                    'signature': sign(self.key, self.session, self.p)}

    def test_signature_and_canonical_bytes(self):
        self.assertEqual(approval_payload(self.session, self.p),
            '\n'.join(['leomux.approve.v1', self.session, 'test', self.p['nonce'], self.p['cmd_hash'], 'approve']))
        self.assertTrue(verify(self.key, self.session, self.p, self.msg))

    def test_wrong_key_nonce_session_command_id_rejected(self):
        self.assertFalse(verify('04' * 32, self.session, self.p, self.msg))
        self.assertFalse(verify(self.key, '05' * 16, self.p, self.msg))
        for field in ('nonce', 'cmd_hash', 'id'):
            p = {**self.p, field: 'changed'}
            self.assertFalse(verify(self.key, self.session, p, self.msg))
        for signature in (None, 10, '', 'z' * 64, [], {}):
            self.assertFalse(verify(self.key, self.session, self.p, {**self.msg, 'signature': signature}))

    def test_separate_secrets_permissions_persistence(self):
        with tempfile.TemporaryDirectory() as home:
            tok, key = load_secret(home, 'token'), load_secret(home, 'approval-key')
            self.assertNotEqual(tok, key)
            self.assertEqual(tok, load_secret(home, 'token'))
            for name in ('token', 'approval-key'):
                self.assertEqual(os.stat(os.path.join(home, name)).st_mode & 0o777, 0o600)

    def test_critical_and_outside_sandbox_refused_even_when_quoted(self):
        for cmd in ('rm -rf ~/x', 'rm -r -f ~/x', "'rm' '-rf' ~/x", 'sudo id', "s'u' -c id",
                    'tsu', '/sbin/su', 'dd if=x of=y', 'mkfs.ext4 x', 'cat /system/build.prop',
                    'ls /data', 'ls ~/storage/downloads', 'ls /sdcard', 'cat ~/.leomux/token',
                    'cat ~/.leomux/approval-key'):
            with self.subTest(cmd=cmd):
                self.assertEqual(risk.risk_for(cmd)['level'], 'critical')

    def test_newline_terminated_oversize_is_rejected(self):
        with self.assertRaises(protocol.ProtocolError):
            protocol.Framer().feed(b' ' * protocol.MAX_LINE + b'\n')
