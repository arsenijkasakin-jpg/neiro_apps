import json
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

import pyautogui
import pyttsx3
import requests
import speech_recognition as sr

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "wake_word": "джарвис",
    "language": "ru-RU",
    "ollama_url": "http://127.0.0.1:11434/api/chat",
    "ollama_model": "qwen2.5:3b",
    "listen_timeout": 5,
    "phrase_time_limit": 10,
}


def load_config() -> dict:
    result = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            result.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    else:
        CONFIG_PATH.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return result


class Jarvis:
    def __init__(self, config: dict):
        self.config = config
        self.recognizer = sr.Recognizer()
        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", 185)
        self.tts.setProperty("volume", 1.0)
        self.history = [{
            "role": "system",
            "content": (
                "Ты — голосовой помощник по имени Джарвис. Отвечай по-русски, "
                "кратко и понятно. Не утверждай, что выполнила действие, если оно "
                "не было выполнено программой."
            ),
        }]

    def speak(self, text: str) -> None:
        print(f"Джарвис: {text}")
        self.tts.say(text)
        self.tts.runAndWait()

    def listen(self) -> Optional[str]:
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                print("🎙️ Слушаю...")
                audio = self.recognizer.listen(
                    source,
                    timeout=float(self.config["listen_timeout"]),
                    phrase_time_limit=float(self.config["phrase_time_limit"]),
                )
        except (sr.WaitTimeoutError, OSError) as exc:
            print(f"Микрофон недоступен: {exc}")
            return None

        try:
            text = self.recognizer.recognize_google(
                audio, language=self.config["language"]
            )
            print(f"Ты: {text}")
            return text.lower().strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            self.speak("Распознавание речи сейчас недоступно.")
            print(exc)
            return None

    def ask_brain(self, prompt: str) -> str:
        self.history.append({"role": "user", "content": prompt})
        try:
            response = requests.post(
                self.config["ollama_url"],
                json={
                    "model": self.config["ollama_model"],
                    "messages": self.history[-10:],
                    "stream": False,
                },
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            answer = data["message"]["content"].strip()
        except requests.RequestException:
            answer = (
                "Локальная нейросеть не отвечает. Проверь Ollama и модель "
                f"{self.config['ollama_model']}."
            )
        except (ValueError, KeyError, TypeError):
            answer = "Не удалось разобрать ответ локальной модели."
        self.history.append({"role": "assistant", "content": answer})
        return answer

    def open_app(self, name: str) -> bool:
        apps = {
            "калькулятор": ["calc.exe"],
            "блокнот": ["notepad.exe"],
            "проводник": ["explorer.exe"],
            "терминал": ["cmd.exe"],
        }
        command = apps.get(name)
        if not command:
            return False
        subprocess.Popen(command)
        return True

    def handle_command(self, text: str) -> Optional[str]:
        if text in {"выход", "завершить работу", "закрой помощника"}:
            return "__EXIT__"

        if text.startswith("открой "):
            target = text.removeprefix("открой ").strip()
            if self.open_app(target):
                return f"Открываю {target}."
            if target.startswith(("http://", "https://")):
                webbrowser.open(target)
                return "Открываю сайт."
            if "." in target and " " not in target:
                webbrowser.open("https://" + target)
                return "Открываю страницу."

        if text.startswith("поиск "):
            query = text.removeprefix("поиск ").strip()
            if query:
                webbrowser.open(
                    "https://www.google.com/search?q=" + requests.utils.quote(query)
                )
                return "Открываю поиск."

        if text in {"сделай скриншот", "снимок экрана"}:
            out = Path.home() / "Pictures" / "Jarvis_Screenshot.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            pyautogui.screenshot(str(out))
            return f"Скриншот сохранён в {out}."

        if text in {"заблокируй компьютер", "заблокируй пк"}:
            subprocess.run(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                check=False,
            )
            return "Блокирую компьютер."

        if text in {"выключи компьютер", "выключи пк"}:
            return "__CONFIRM_SHUTDOWN__"

        return None

    def run(self) -> None:
        self.speak(
            "Джарвис запущен. Скажи команду. Для завершения скажи: выход."
        )
        wake = self.config["wake_word"].lower()

        while True:
            text = self.listen()
            if not text:
                continue

            if wake in text:
                text = text.replace(wake, "", 1).strip()

            action = self.handle_command(text)

            if action == "__EXIT__":
                self.speak("До связи.")
                return

            if action == "__CONFIRM_SHUTDOWN__":
                self.speak(
                    "Для выключения требуется подтверждение. "
                    "Введи ВЫКЛЮЧИТЬ в консоли."
                )
                if input("> ").strip().lower() == "выключить":
                    subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
                continue

            if action:
                self.speak(action)
            else:
                self.speak(self.ask_brain(text))


if __name__ == "__main__":
    try:
        Jarvis(load_config()).run()
    except KeyboardInterrupt:
        print("\nЗавершено.")
    except Exception as exc:
        print(f"Критическая ошибка: {exc}")
        sys.exit(1)
