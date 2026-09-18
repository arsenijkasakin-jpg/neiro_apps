import json, subprocess, threading, webbrowser
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui, pyttsx3, requests
import speech_recognition as sr

BASE=Path(__file__).resolve().parent
CFG=BASE/"config.json"
DEFAULT={
    "wake_word":"джарвис","language":"ru-RU",
    "ollama_url":"http://127.0.0.1:11434",
    "ollama_model":"qwen2.5:3b",
    "listen_timeout":5,"phrase_time_limit":10,
    "tts_rate":185,"tts_volume":1.0
}

def load_config():
    data=DEFAULT.copy()
    if CFG.exists():
        try:
            data.update(json.loads(CFG.read_text(encoding="utf-8")))
        except (OSError,json.JSONDecodeError):
            pass
    else:
        CFG.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    return data

class Core:
    def __init__(self,cfg):
        self.cfg=cfg
        self.rec=sr.Recognizer()
        self.tts=pyttsx3.init()
        self.tts.setProperty("rate",int(cfg.get("tts_rate",185)))
        self.tts.setProperty("volume",float(cfg.get("tts_volume",1.0)))
        self.history=[{"role":"system","content":
            "Ты Джарвис, локальный голосовой помощник. Отвечай только на русском, "
            "естественно и по делу. Не утверждай, что выполнила действие, если программа его не выполнила."}]
        self.pick_ru_voice()

    def pick_ru_voice(self):
        try:
            for v in self.tts.getProperty("voices"):
                s=f"{v.id} {v.name}".lower()
                if any(x in s for x in ("ru-ru","russian","рус","ru_")):
                    self.tts.setProperty("voice",v.id); break
        except Exception:
            pass

    def base_url(self):
        return self.cfg.get("ollama_url",DEFAULT["ollama_url"]).rstrip("/")

    def models(self):
        r=requests.get(self.base_url()+"/api/tags",timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models",[]) if m.get("name")]

    def ask(self,text,model):
        self.history.append({"role":"user","content":text})
        r=requests.post(
            self.base_url()+"/api/chat",
            json={"model":model,"messages":self.history[-12:],"stream":False,
                  "options":{"temperature":0.45}},
            timeout=90
        )
        r.raise_for_status()
        ans=r.json().get("message",{}).get("content","").strip()
        if not ans: raise RuntimeError("Ollama вернула пустой ответ")
        self.history.append({"role":"assistant","content":ans})
        return ans

    def speak(self,text):
        try:
            self.tts.say(text); self.tts.runAndWait()
        except Exception:
            pass

    def listen(self):
        with sr.Microphone() as src:
            self.rec.adjust_for_ambient_noise(src,duration=.35)
            audio=self.rec.listen(src,
                timeout=float(self.cfg.get("listen_timeout",5)),
                phrase_time_limit=float(self.cfg.get("phrase_time_limit",10)))
        return self.rec.recognize_google(audio,language=self.cfg.get("language","ru-RU")).strip()

    def command(self,text):
        t=" ".join(text.lower().split())
        if t in {"выход","закройся","заверши работу"}: return "__EXIT__"
        if t.startswith("открой ") or t.startswith("запусти "):
            target=t.split(" ",1)[1].strip()
            apps={"калькулятор":["calc.exe"],"блокнот":["notepad.exe"],
                  "проводник":["explorer.exe"],"терминал":["cmd.exe"],
                  "диспетчер задач":["taskmgr.exe"]}
            if target in apps:
                subprocess.Popen(apps[target]); return f"Открываю {target}."
            if target.startswith(("http://","https://")):
                webbrowser.open(target); return "Открываю сайт."
            if "." in target and " " not in target:
                webbrowser.open("https://"+target); return "Открываю страницу."
        if t.startswith("поиск "):
            q=t[6:].strip()
            if q:
                webbrowser.open("https://www.google.com/search?q="+requests.utils.quote(q))
                return "Открываю результаты поиска."
        if t in {"сделай скриншот","снимок экрана"}:
            p=Path.home()/"Pictures"/"Jarvis_Screenshot.png"; p.parent.mkdir(parents=True,exist_ok=True)
            pyautogui.screenshot(str(p)); return f"Скриншот сохранён: {p}"
        if t in {"заблокируй компьютер","заблокируй пк"}:
            subprocess.run(["rundll32.exe","user32.dll,LockWorkStation"],check=False)
            return "Блокирую компьютер."
        if t in {"выключи компьютер","выключи пк"}: return "__SHUTDOWN__"
        if t in {"перезагрузи компьютер","перезагрузи пк"}: return "__RESTART__"
        return None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg=load_config(); self.core=Core(self.cfg)
        self.listening=False; self.auto=False
        self.title("JARVIS — локальный голосовой помощник")
        self.geometry("1000x650"); self.minsize(820,560); self.configure(bg="#070c13")
        self.build()
        self.refresh_models()
        self.add("system","Джарвис готов. Можно писать сообщение или нажать «Слушать».")
        self.protocol("WM_DELETE_WINDOW",self.close)

    def build(self):
        top=tk.Frame(self,bg="#0d1621",height=60); top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top,text="JARVIS",font=("Segoe UI",20,"bold"),fg="#f0f3f6",bg="#0d1621").pack(side="left",padx=(18,8),pady=12)
        tk.Label(top,text="ГОЛОСОВОЙ АССИСТЕНТ",font=("Segoe UI",9),fg="#7d8b9e",bg="#0d1621").pack(side="left",pady=17)
        self.status=tk.Label(top,text="● Готов",font=("Segoe UI",10,"bold"),fg="#49d17d",bg="#0d1621"); self.status.pack(side="right",padx=18)

        body=tk.Frame(self,bg="#070c13"); body.pack(fill="both",expand=True,padx=12,pady=12)
        side=tk.Frame(body,bg="#0d1621",width=230); side.pack(side="left",fill="y",padx=(0,10)); side.pack_propagate(False)
        tk.Label(side,text="СИСТЕМА",fg="#78879a",bg="#0d1621",font=("Segoe UI",9,"bold")).pack(anchor="w",padx=14,pady=(14,6))
        tk.Label(side,text="Модель Ollama",fg="#c7d0db",bg="#0d1621",font=("Segoe UI",9)).pack(anchor="w",padx=14)
        self.model=tk.StringVar(value=self.cfg.get("ollama_model","qwen2.5:3b"))
        self.box=ttk.Combobox(side,textvariable=self.model,state="normal"); self.box.pack(fill="x",padx=14,pady=(4,8))
        for title,fn in [("Проверить Ollama",self.check),("Обновить модели",self.refresh_models)]:
            tk.Button(side,text=title,command=fn,bg="#172334",fg="#edf1f4",activebackground="#26374e",activeforeground="white",relief="flat",cursor="hand2",pady=7).pack(fill="x",padx=14,pady=2)
        tk.Label(side,text="БЫСТРЫЕ КОМАНДЫ",fg="#78879a",bg="#0d1621",font=("Segoe UI",9,"bold")).pack(anchor="w",padx=14,pady=(22,6))
        quick=[("🌐 Браузер",lambda:webbrowser.open("https://www.google.com")),
               ("📁 Проводник",lambda:subprocess.Popen(["explorer.exe"])),
               ("📝 Блокнот",lambda:subprocess.Popen(["notepad.exe"])),
               ("📸 Скриншот",lambda:self.run("сделай скриншот")),
               ("🔒 Заблокировать",lambda:self.run("заблокируй компьютер"))]
        for title,fn in quick:
            tk.Button(side,text=title,command=fn,bg="#101b29",fg="#c7d0db",activebackground="#213149",activeforeground="white",relief="flat",cursor="hand2",pady=6).pack(fill="x",padx=14,pady=2)
        self.auto_var=tk.BooleanVar(value=False)
        tk.Checkbutton(side,text="Слушать после ответа",variable=self.auto_var,command=self.toggle_auto,bg="#0d1621",fg="#aeb9c7",selectcolor="#172334",activebackground="#0d1621",activeforeground="white").pack(anchor="w",padx=10,pady=(18,0))

        chat=tk.Frame(body,bg="#0d1621"); chat.pack(side="left",fill="both",expand=True)
        tk.Label(chat,text="ЧАТ",fg="#edf1f4",bg="#0d1621",font=("Segoe UI",10,"bold")).pack(anchor="w",padx=15,pady=(13,7))
        area=tk.Frame(chat,bg="#09111a"); area.pack(fill="both",expand=True,padx=12,pady=(0,9))
        self.text=tk.Text(area,bg="#09111a",fg="#dce3eb",insertbackground="white",font=("Segoe UI",10),wrap="word",relief="flat",padx=12,pady=12,state="disabled")
        self.text.pack(side="left",fill="both",expand=True); sb=ttk.Scrollbar(area,command=self.text.yview); sb.pack(side="right",fill="y"); self.text.configure(yscrollcommand=sb.set)
        for tag,col in (("user","#8fc1ff"),("jarvis","#f1f3f5"),("system","#718096"),("error","#ef6976")): self.text.tag_configure(tag,foreground=col,spacing1=8)
        controls=tk.Frame(chat,bg="#0d1621"); controls.pack(fill="x",padx=12,pady=(0,12))
        self.entry=tk.Entry(controls,bg="#121e2c",fg="#edf1f4",insertbackground="white",relief="flat",font=("Segoe UI",10))
        self.entry.pack(side="left",fill="x",expand=True,ipady=10,padx=(0,7)); self.entry.bind("<Return>",lambda e:self.send())
        self.listen_btn=tk.Button(controls,text="🎙 Слушать",command=self.listen,bg="#edf1f4",fg="#0c131a",activebackground="white",relief="flat",cursor="hand2",font=("Segoe UI",9,"bold"),padx=14,pady=9)
        self.listen_btn.pack(side="left",padx=(0,6))
        tk.Button(controls,text="Отправить",command=self.send,bg="#172334",fg="#edf1f4",activebackground="#26374e",activeforeground="white",relief="flat",cursor="hand2",font=("Segoe UI",9,"bold"),padx=14,pady=9).pack(side="left")

    def add(self,role,msg):
        self.text.configure(state="normal")
        self.text.insert("end",{"user":"Ты","jarvis":"Джарвис","system":"Система","error":"Ошибка"}.get(role,"Система")+": ",role)
        self.text.insert("end",msg+"\n\n"); self.text.configure(state="disabled"); self.text.see("end")

    def set_status(self,msg,color):
        self.after(0,lambda:self.status.configure(text="● "+msg,fg=color))

    def refresh_models(self):
        self.set_status("Подключение...", "#e5c85d")
        def w():
            try:
                ms=self.core.models()
                self.after(0,lambda:(self.box.configure(values=ms),self.set_model(ms)))
                self.set_status("Готов","#49d17d")
            except Exception as e:
                self.set_status("Ollama не подключена","#ef6976")
                self.after(0,lambda:self.add("error",f"Ollama недоступна: {e}"))
        threading.Thread(target=w,daemon=True).start()

    def set_model(self,ms):
        if ms and self.model.get() not in ms: self.model.set(ms[0])

    def check(self):
        def w():
            try:
                ms=self.core.models(); self.after(0,lambda:messagebox.showinfo("Ollama","Подключение работает.\n\n"+("\n".join(ms) if ms else "Моделей нет.")))
            except Exception as e:
                self.after(0,lambda:messagebox.showerror("Ollama",f"Не удалось подключиться.\n\n{e}"))
        threading.Thread(target=w,daemon=True).start()

    def send(self):
        q=self.entry.get().strip()
        if q: self.entry.delete(0,"end"); self.add("user",q); self.run(q)

    def listen(self):
        if self.listening:return
        self.listening=True; self.listen_btn.configure(text="🎙 Слушаю…",state="disabled",bg="#172334",fg="white"); self.set_status("Слушаю","#e5c85d")
        def w():
            try:
                raw=self.core.listen(); self.after(0,lambda:self.add("user",raw))
                wake=self.cfg.get("wake_word","джарвис").lower(); q=raw.lower().replace(wake,"",1).strip() if wake in raw.lower() else raw.lower()
                self.run(q)
            except sr.WaitTimeoutError:self.after(0,lambda:self.add("system","Я не услышал команду."))
            except sr.UnknownValueError:self.after(0,lambda:self.add("system","Не удалось разобрать речь."))
            except sr.RequestError as e:self.after(0,lambda:self.add("error",f"Распознавание речи недоступно: {e}"))
            except OSError as e:self.after(0,lambda:self.add("error",f"Не удалось открыть микрофон: {e}"))
            finally:self.after(0,self.finish_listen)
        threading.Thread(target=w,daemon=True).start()

    def finish_listen(self):
        self.listening=False; self.listen_btn.configure(text="🎙 Слушать",state="normal",bg="#edf1f4",fg="#0c131a")
        if not self.auto:self.set_status("Готов","#49d17d")

    def toggle_auto(self):
        self.auto=bool(self.auto_var.get())
        if self.auto and not self.listening:self.after(300,self.listen)

    def run(self,q):
        self.set_status("Обработка","#e5c85d")
        def w():
            action=self.core.command(q)
            if action=="__EXIT__": self.after(0,self.close); return
            if action in {"__SHUTDOWN__","__RESTART__"}:
                title="Выключение" if action=="__SHUTDOWN__" else "Перезагрузка"
                if self.confirm(title,f"{title}ить компьютер прямо сейчас?"):
                    cmd=["shutdown","/s" if action=="__SHUTDOWN__" else "/r","/t","0"]; subprocess.run(cmd,check=False)
                else:self.after(0,lambda:self.add("jarvis","Отмена. Команда не выполнена."))
                self.set_status("Готов","#49d17d"); return
            if action:
                self.after(0,lambda:self.add("jarvis",action)); threading.Thread(target=self.core.speak,args=(action,),daemon=True).start(); self.set_status("Готов","#49d17d"); return
            try:
                ans=self.core.ask(q,self.model.get().strip() or self.cfg.get("ollama_model"))
            except Exception as e:
                ans=f"Не могу получить ответ от Ollama. Проверь, что Ollama запущена и выбранная модель установлена.\n\nОшибка: {e}"
                self.after(0,lambda:self.add("error",ans)); self.set_status("Ошибка Ollama","#ef6976"); return
            self.after(0,lambda:self.add("jarvis",ans)); threading.Thread(target=self.core.speak,args=(ans,),daemon=True).start(); self.set_status("Готов","#49d17d")
        threading.Thread(target=w,daemon=True).start()

    def confirm(self,title,msg):
        box={"v":False}; done=threading.Event()
        def ask(): box["v"]=messagebox.askyesno(title,msg,parent=self); done.set()
        self.after(0,ask); done.wait(); return box["v"]

    def close(self):
        try:self.core.tts.stop()
        except Exception:pass
        self.destroy()

if __name__=="__main__":
    App().mainloop()
