"""Commander tmux runner, ported from 4ac394b. Sourced commands preserve cwd/env."""
import os, re, shlex, subprocess, time
from contextlib import nullcontext
ANSI_RE = re.compile(r"\x1b\[[0-9;?<>=]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][0-9A-Za-z]|\x1b[=>78DEHMc]")
SENTINEL_RE = re.compile(r"\x1eLEO (\S+) (-?\d+)\x1e")

class Shell:
    """Persistent bash inside tmux. Commands are written to ~/.leo/cmds/<id>.sh and
    *sourced* (so cd/export persist); a sentinel printed via printf with \\036 bytes
    carries the exit code. Output is read from a pipe-pane log."""

    def __init__(self, home, session="leo", tmux_socket=None):
        self.home, self.session = home, session
        self.tmux = ["tmux"] + (["-L", tmux_socket] if tmux_socket else [])
        self.cmd_dir = os.path.join(home, "cmds")
        self.log_path = os.path.join(home, "pty.log")
        os.makedirs(self.cmd_dir, mode=0o700, exist_ok=True)

    def _t(self, *a, check=False):
        return subprocess.run(self.tmux + list(a), capture_output=True, text=True, check=check,
                              env={k: v for k, v in os.environ.items() if k not in ("XAI_API_KEY", "LEO_GROK_MODEL")})

    def alive(self):
        return self._t("has-session", "-t", self.session).returncode == 0

    def ensure(self):
        if not self.alive():
            rc = os.path.join(self.home, "rc.bash")
            fd = os.open(rc, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write('[ -f ~/.bashrc ] && . ~/.bashrc\nPS1="\\[\\e[35m\\]leo\\[\\e[0m\\]:\\w\\$ "\n'
                        "bind 'set enable-bracketed-paste off' 2>/dev/null\nHISTCONTROL=ignorespace\n")
            self._t("new-session", "-d", "-s", self.session, "-x", "400", "-y", "50", "-c", os.path.expanduser("~"),
                    "bash --rcfile %s -i" % shlex.quote(rc), check=True)
            time.sleep(0.3)
        fd = os.open(self.log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        os.close(fd)
        self._t("pipe-pane", "-t", self.session)  # close any old pipe
        self._t("pipe-pane", "-t", self.session, "cat >> %s" % shlex.quote(self.log_path), check=True)

    def run(self, cid, cmd, on_output, max_runtime=900, guard=None, gate=None):
        """Blocking. Calls on_output(text) as output arrives. Returns exit code."""
        path = os.path.join(self.cmd_dir, cid + ".sh")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(cmd.rstrip("\n") + "\n")
        # leading space = not saved in history (HISTCONTROL=ignorespace)
        line = " . %s; printf '\\036LEO %s %%s\\036\\n' $?" % (shlex.quote(path), cid)
        start = os.path.getsize(self.log_path) if os.path.exists(self.log_path) else 0
        with gate if gate is not None else nullcontext():
            if guard is not None and not guard():
                return -2
            self.ensure()
            self._t("send-keys", "-t", self.session, "-l", line, check=True)
            self._t("send-keys", "-t", self.session, "Enter", check=True)
        marker, buf, pos = "cmds/%s.sh" % cid, "", start
        t0, last_data, interrupted = time.time(), time.time(), False
        while True:
            time.sleep(0.15)
            with open(self.log_path, "rb") as f:
                f.seek(pos)
                data = f.read()
            pos += len(data)
            if data:
                last_data = time.time()
                buf += data.decode("utf-8", "replace")
            m = SENTINEL_RE.search(buf)
            if m and m.group(1) == cid:
                self._emit(buf[:m.start()], marker, on_output, final=True)
                return int(m.group(2))
            # emit complete lines; keep partial line unless idle for 1s (prompts)
            cut = buf.rfind("\n") + 1
            if cut == 0 and buf and time.time() - last_data > 1.0 and "\x1e" not in buf:
                cut = len(buf)
            if cut:
                self._emit(buf[:cut], marker, on_output)
                buf = buf[cut:]
            if not self.alive():
                self._emit(buf, marker, on_output, final=True)
                on_output("\n[leo] shell exited; a fresh session will start next time\n")
                return -1
            if interrupted and time.time() - t0 > max_runtime + 3:
                self._t("kill-session", "-t", self.session)
                return -2
            if max_runtime and not interrupted and time.time() - t0 > max_runtime:
                interrupted = True
                on_output("\n[leo] max runtime %ss hit, sending Ctrl-C\n" % max_runtime)
                self._t("send-keys", "-t", self.session, "C-c")

    @staticmethod
    def _emit(text, marker, on_output, final=False):
        text = ANSI_RE.sub("", text).replace("\r", "")
        lines = [ln for ln in text.split("\n") if marker not in ln and "\\036LEO" not in ln]
        text = "\n".join(lines)
        if final:
            text = re.sub(r"\n?[^\n]*leo:[^\n]*\$ ?$", "", text)  # trailing prompt
        if text.strip():
            on_output(text if text.endswith("\n") or not final else text + "\n")
