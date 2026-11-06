"""Nonce-bound approvals. Separate key: a socket token NEVER authorizes execution."""
import hashlib
import hmac
import os
import secrets


def load_secret(home, name):
    path = os.path.join(home, name)
    if not os.path.exists(path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(secrets.token_hex(32))
    os.chmod(path, 0o600)
    with open(path) as f:
        value = f.read().strip()
    if len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('invalid local secret; repair %s offline' % name)
    return value


def approval_payload(session, proposal):
    # Exact same UTF-8 bytes as native Android control; never JSON canonicalization.
    return '\n'.join(('leomux.approve.v1', session, proposal['id'], proposal['nonce'],
                      proposal['cmd_hash'], 'approve'))


def sign(key, session, proposal):
    return hmac.new(bytes.fromhex(key), approval_payload(session, proposal).encode(),
                    hashlib.sha256).hexdigest()


def verify(key, session, proposal, msg):
    signature = msg.get('signature', '')
    return (isinstance(signature, str) and len(signature) == 64 and
            msg.get('nonce') == proposal['nonce'] and
            msg.get('session_id') == session and
            hmac.compare_digest(sign(key, session, proposal), signature))
