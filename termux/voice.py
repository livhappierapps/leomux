"""Termux:API voice path; no arbitrary executable or shell from the wire."""
import subprocess


class Voice:
    def __init__(self, mock=False):
        self.mock = mock

    def listen(self):
        if self.mock:
            return 'test voice transcript'
        result = subprocess.run(['termux-speech-to-text'], capture_output=True,
                                text=True, check=True, timeout=60)
        text = result.stdout.strip()
        if not text:
            raise ValueError('No speech recognized. Check Termux:API microphone permission.')
        return text[:8000]

    def speak(self, text):
        if not self.mock:
            subprocess.run(['termux-tts-speak'], input=text[:4000], capture_output=True,
                           text=True, check=True, timeout=60)
