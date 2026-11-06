import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import protocol  # noqa: E402


class Framing(unittest.TestCase):
    def test_roundtrip_and_newlines_escaped(self):
        m = {"type": "propose", "id": "a1", "cmd": "echo 'a\nb' && ls", "reason": "ünïcode"}
        data = protocol.encode(m)
        self.assertEqual(data.count(b"\n"), 1)
        self.assertEqual(protocol.Framer().feed(data), [m])

    def test_split_and_merged_reads(self):
        a, b = protocol.encode({"type": "status"}), protocol.encode({"type": "ping", "x": 1})
        f = protocol.Framer()
        stream = a + b
        got = []
        for i in range(0, len(stream), 3):  # 3-byte TCP reads
            got += f.feed(stream[i:i + 3])
        self.assertEqual(got, [{"type": "status"}, {"type": "ping", "x": 1}])
        self.assertEqual(protocol.Framer().feed(a + b), got)

    def test_blank_lines_ignored(self):
        self.assertEqual(protocol.Framer().feed(b"\n\r\n" + protocol.encode({"type": "ping"})), [{"type": "ping"}])

    def test_rejects_bad(self):
        for bad in (b"not json\n", b"[1,2]\n", b'{"no":"type"}\n', b'{"type":5}\n'):
            with self.subTest(bad=bad), self.assertRaises(protocol.ProtocolError):
                protocol.Framer().feed(bad)
        with self.assertRaises(protocol.ProtocolError):
            protocol.encode({"cmd": "x"})

    def test_too_long(self):
        f = protocol.Framer()
        with self.assertRaises(protocol.ProtocolError):
            f.feed(b"x" * (protocol.MAX_LINE + 10))
        with self.assertRaises(protocol.ProtocolError):
            protocol.encode({"type": "output", "data": "x" * protocol.MAX_LINE})

    def test_chunk_text(self):
        self.assertEqual("".join(protocol.chunk_text("ab" * 5000, 4096)), "ab" * 5000)
        self.assertEqual(protocol.chunk_text(""), [""])


if __name__ == "__main__":
    unittest.main()
