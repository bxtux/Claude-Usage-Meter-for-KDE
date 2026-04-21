from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


class Notifier:
    def __init__(self, play_sound: bool) -> None:
        self.play_sound = play_sound
        self.notify_send = shutil.which("notify-send")
        self.paplay = shutil.which("paplay")
        self.aplay = shutil.which("aplay")

    def notify_threshold(self, percent: int, reset_text: str) -> None:
        title = "Claude Usage Meter"
        body = f"Usage session actuelle: {percent}%\n{reset_text}"

        if self.notify_send:
            subprocess.run([self.notify_send, title, body], check=False)

        if self.play_sound:
            self._play_sound()

    def _play_sound(self) -> None:
        sound_oga = Path("/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga")
        sound_wav = Path("/usr/share/sounds/alsa/Front_Center.wav")

        if self.paplay and sound_oga.exists():
            subprocess.run([self.paplay, str(sound_oga)], check=False)
            return

        if self.aplay and sound_wav.exists():
            subprocess.run([self.aplay, str(sound_wav)], check=False)
