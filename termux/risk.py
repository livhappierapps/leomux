"""Risk tagger + security alert scanner for Leo. Stdlib only.

risk_for(cmd)          -> {"level": "low|medium|high|critical", "tags": [...]}
command_alerts(cmd)    -> [{"level","msg"}]  (pre-run security notes)
output_alerts(text)    -> [{"level","msg"}]  (post-run security notes)
"""
import re, shlex

LEVELS = ["low", "medium", "high", "critical"]

# (tag, level, regex). Order doesn't matter; highest level wins.
RULES = [
    ("fork-bomb",      "critical", r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),
    # "rm-rf" is detected in code (_rm_rf) because flags can be split: rm -r -f
    ("rm",             "medium",   r"\brm\s"),
    ("dd",             "critical", r"\bdd\s+.*\bof="),
    ("mkfs",           "critical", r"\bmkfs(\.\w+)?\b|\bmke2fs\b|\bwipefs\b"),
    ("block-device",   "critical", r">\s*/dev/(block|sd[a-z]|mmcblk|nvme)"),
    ("pipe-to-shell",  "critical", r"\b(curl|wget|fetch)\b[^|;&]*\|\s*(sudo\s+|tsu\s+)?(ba|z|da)?sh\b"),
    ("pipe-to-interp", "high",     r"\b(curl|wget)\b[^|;&]*\|\s*(python3?|perl|ruby|node)\b"),
    ("base64-exec",    "critical", r"base64\s+(-d|--decode)[^|;&]*\|\s*(ba|z)?sh\b|\beval\s+\"?\$\(.*base64"),
    ("eval",           "medium",   r"\beval\s"),
    ("pkg-install",    "medium",   r"\b(pkg|apt|apt-get)\s+(install|upgrade|remove|purge|uninstall)\b"),
    ("pip-install",    "medium",   r"\bpip3?\s+install\b"),
    ("npm-install",    "medium",   r"\bnpm\s+(i|install|add)\b|\byarn\s+add\b|\bpnpm\s+(add|install)\b"),
    ("gem/cargo",      "medium",   r"\b(gem|cargo)\s+install\b"),
    ("root",           "critical",     r"(^|[;&|]\s*|\s)(su|sudo|tsu|doas)(\s|$)"),
    ("chmod-system",   "high",     r"\bch(mod|own|grp)\b.*\s/(system|vendor|data|etc|bin|sbin|usr|proc|sys)\b"),
    ("chmod-recursive","medium",   r"\bch(mod|own)\s+-[a-zA-Z]*R"),
    ("setuid",         "high",     r"\bchmod\s+([ugoa]*\+[rwx]*s|[0-7]?[4-7][0-7]{3})\b"),
    ("world-writable", "medium",   r"\bchmod\s+(-R\s+)?(o\+w|a\+w|0?[0-7][0-7][2367]\b|777)"),
    ("write-system",   "critical", r"(>|tee\s+(-a\s+)?|cp\s.*|mv\s.*)\s*/(system|vendor|data/(?!data/com\.termux))\S*"),
    ("mount",          "high",     r"\bmount\s+.*(-o\s*\S*rw|remount)|\bumount\b"),
    ("reboot",         "high",     r"\b(reboot|shutdown|poweroff|halt)\b|\bsvc\s+power\b"),
    ("firewall",       "high",     r"\b(iptables|ip6tables|nft)\b"),
    ("selinux",        "high",     r"\bsetenforce\b|\bsetprop\b"),
    ("pm/am",          "medium",   r"\b(pm\s+(uninstall|clear|disable|grant|revoke)|cmd\s+package)\b"),
    ("kill",           "medium",   r"\b(kill\s+-9|killall|pkill)\b"),
    ("network-listen", "medium",   r"\b(nc|ncat|netcat|socat)\b.*\s-[a-zA-Z]*l|\bhttp\.server\b|--host\s+0\.0\.0\.0|\s0\.0\.0\.0:"),
    ("scan",           "medium",   r"\b(nmap|masscan|hydra|sqlmap|nikto|msfconsole|msfvenom)\b"),
    ("history-wipe",   "medium",   r"\bhistory\s+-c\b|>\s*~/\.bash_history|\bshred\b"),
    ("crontab",        "medium",   r"\bcrontab\s+-r\b"),
    ("leo-self",       "high",     r"\.leo/token|leo_server\.py|\bpkill\b.*leo"),
]
_COMPILED = [(t, l, re.compile(p)) for t, l, p in RULES]


def _rm_rf(cmd):
    for m in re.finditer(r"\brm\s+([^;&|\n]*)", cmd):
        flags = "".join(t[1:] for t in m.group(1).split() if t.startswith("-") and not t.startswith("--"))
        longs = m.group(1)
        if ("r" in flags or "R" in flags or "--recursive" in longs) and ("f" in flags or "--force" in longs):
            return True
    return False


def risk_for(cmd):
    # Normalize simple shell quoting/escapes as well as scanning original text.
    # This is a warning/deny heuristic, NOT a general shell sandbox.
    try:
        normalized = " ".join(shlex.split(cmd))
    except ValueError:
        normalized = cmd
    cmd = cmd + "\n" + normalized
    tags, level = [], "low"
    forbidden = r"(?<![A-Za-z0-9])/(?:system|data|vendor|root|sdcard|storage|proc|sys|dev)(?:/|\b)"
    if re.search(forbidden, cmd):
        tags, level = ["outside-termux"], "critical"
    if re.search(r"(?:\.leo(?:mux)?/|leo_server\.py|approval-key|\.ssh/|id_rsa|id_ed25519|\.netrc|\.env\b)", cmd):
        tags.append("protected-state")
        level = "critical"
    # Never allow privileges, including absolute/quoted executable spellings.
    if re.search(r"(?:^|[\s;&|/])(su|sudo|tsu|doas)(?:\s|$)", cmd):
        tags.append("root")
        level = "critical"

    if _rm_rf(cmd):
        tags.append("rm-rf")
        level = "critical"
    for tag, lvl, rx in _COMPILED:
        if rx.search(cmd):
            tags.append(tag)
            if LEVELS.index(lvl) > LEVELS.index(level):
                level = lvl
    if "rm-rf" in tags and "rm" in tags:
        tags.remove("rm")
    return {"level": level, "tags": list(dict.fromkeys(tags))}


# ---- security alerts -------------------------------------------------------
SAFE_HOSTS = {
    "github.com", "raw.githubusercontent.com", "objects.githubusercontent.com",
    "pypi.org", "files.pythonhosted.org", "registry.npmjs.org",
    "packages.termux.dev", "packages-cf.termux.dev", "grimler.se",
    "localhost", "127.0.0.1",
}

_CMD_ALERTS = [
    ("high",   "Touches credentials/keys", r"(\.ssh/|id_rsa|id_ed25519|\.netrc|\.aws/credentials|\.git-credentials|/etc/shadow|\.leo/token|\.env\b|keystore|\.pem\b)"),
    ("high",   "Sets SUID/SGID bit",        r"\bchmod\s+([ugoa]*\+[rwx]*s|[0-7]?[4-7][0-7]{3})\b"),
    ("medium", "Makes files world-writable", r"\bchmod\s+(-R\s+)?(o\+w|a\+w|0?[0-7][0-7][2367]\b|777)"),
    ("medium", "Opens a listening port",    r"\b(nc|ncat|netcat|socat)\b.*\s-[a-zA-Z]*l|\bhttp\.server\b|0\.0\.0\.0"),
]
_OUT_ALERTS = [
    ("high",   "Private key in output",      r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("high",   "Possible secret in output",  r"(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,}|xox[bp]-[A-Za-z0-9-]{10,}|(?i:password|passwd|secret|api[_-]?key)\s*[=:]\s*\S{4,})"),
    ("medium", "Port listening on all interfaces", r"(0\.0\.0\.0|\*|\[::\]):\d+\s.*LISTEN|LISTEN\s.*(0\.0\.0\.0|\*|\[::\]):\d+"),
    ("medium", "SUID binary listed",         r"^-[r-][w-][sS]"),
    ("low",    "World-writable entry listed", r"^[d-][r-][w-][xs-][r-][w-][xs-][r-]w[xtT-]"),
]
_URL_HOST = re.compile(r"\b(?:https?|ftp)://([^/\s:'\"]+)")
_SSH_HOST = re.compile(r"\b(?:ssh|scp|nc|ncat|telnet)\s+(?:-\S+\s+)*(?:\S+@)?([A-Za-z0-9][\w.-]*\.[A-Za-z]{2,}|\d+\.\d+\.\d+\.\d+)")


def _host_ok(host, allow):
    host = host.lower()
    return any(host == h or host.endswith("." + h) for h in allow)


def command_alerts(cmd, allow=SAFE_HOSTS):
    out = [{"level": l, "msg": m} for l, m, p in _CMD_ALERTS if re.search(p, cmd)]
    hosts = _URL_HOST.findall(cmd) + _SSH_HOST.findall(cmd)
    for h in sorted(set(hosts)):
        if not _host_ok(h, allow):
            out.append({"level": "medium", "msg": "Outbound to unknown host: " + h})
    return out


def output_alerts(text):
    out, seen = [], set()
    for l, m, p in _OUT_ALERTS:
        if m not in seen and re.search(p, text, re.M):
            seen.add(m)
            out.append({"level": l, "msg": m})
    return out
