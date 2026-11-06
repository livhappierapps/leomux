"""Newline-delimited JSON framing for the Leo socket. Stdlib only."""
import json

MAX_LINE = 1 << 20  # 1 MiB per message
VERSION = 2


class ProtocolError(ValueError):
    pass


def encode(msg):
    """dict -> one UTF-8 line (no embedded newlines; json escapes them)."""
    if not isinstance(msg, dict) or "type" not in msg:
        raise ProtocolError("message must be a dict with 'type'")
    data = (json.dumps(msg, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
    if len(data) > MAX_LINE:
        raise ProtocolError("message too large")
    return data


def decode(line):
    try:
        msg = json.loads(line.decode() if isinstance(line, bytes) else line)
    except (ValueError, UnicodeDecodeError) as e:
        raise ProtocolError("bad json: %s" % e)
    if not isinstance(msg, dict) or not isinstance(msg.get("type"), str):
        raise ProtocolError("message must be an object with string 'type'")
    return msg


class Framer:
    """Feed raw bytes, get complete messages. Handles split/merged TCP reads."""

    def __init__(self):
        self.buf = b""

    def feed(self, data):
        self.buf += data
        out = []
        while True:
            i = self.buf.find(b"\n")
            if i < 0:
                if len(self.buf) > MAX_LINE:
                    self.buf = b""
                    raise ProtocolError("line too long")
                return out
            if i + 1 > MAX_LINE:
                self.buf = b""
                raise ProtocolError("line too long")
            line, self.buf = self.buf[:i], self.buf[i + 1:]
            if line.strip():
                out.append(decode(line))


def chunk_text(text, size=4096):
    """Split output into chunks for 'output' messages."""
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]
