import json, queue, threading, time, tkinter as tk
from tkinter import ttk

try:
    import websocket
except ImportError:
    websocket = None

URL = 'ws://127.0.0.1:49124'
BG = '#111827'
BLUE = '#60a5fa'
ORANGE = '#fb923c'

class HUD:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('RL Boost HUD')
        self.root.geometry('270x430+1150+170')
        self.root.configure(bg=BG)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.attributes('-alpha', .92)
        self.root.wm_attributes('-transparentcolor', '#010101') if False else None
        self.q = queue.Queue()
        self.running = True
        self.locked = False
        self.connected = False
        self.last_update = 0
        self.drag_start = None
        self.header = tk.Frame(self.root, bg=BG)
        self.header.pack(fill='x', padx=10, pady=(9,3))
        tk.Label(self.header,text='RL BOOST HUD',font=('Segoe UI',12,'bold'),bg=BG,fg='white').pack(side='left')
        self.status = tk.Label(self.root,text='Connecting to official Stats API…',font=('Segoe UI',9),bg=BG,fg='#9ca3af')
        self.status.pack(anchor='w',padx=10)
        self.controls = tk.Frame(self.root,bg=BG)
        self.controls.pack(fill='x',padx=8,pady=5)
        self.lock_btn = tk.Button(self.controls,text='Click-through: OFF',command=self.toggle_lock,font=('Segoe UI',8),bg='#374151',fg='white',relief='flat')
        self.lock_btn.pack(side='left')
        tk.Button(self.controls,text='Close',command=self.close,font=('Segoe UI',8),bg='#374151',fg='white',relief='flat').pack(side='right')
        self.teams = tk.Frame(self.root,bg=BG)
        self.teams.pack(fill='both',expand=True,padx=10,pady=5)
        self.help = tk.Label(self.root,text='Drag header to move • Ctrl+Shift+H toggles HUD\nUnknown boost is shown as N/A (never guessed)',bg=BG,fg='#9ca3af',font=('Segoe UI',8),justify='left')
        self.help.pack(anchor='w',padx=10,pady=(0,9))
        for widget in (self.header,):
            widget.bind('<ButtonPress-1>',self.start_drag)
            widget.bind('<B1-Motion>',self.drag)
        self.root.bind_all('<Control-Shift-h>',lambda e:self.toggle_visible())
        self.root.bind_all('<Control-Shift-H>',lambda e:self.toggle_visible())
        self.render([])
        self.root.after(100,self.poll)
        threading.Thread(target=self.reader,daemon=True).start()

    def start_drag(self,e):
        self.drag_start=(e.x_root-self.root.winfo_x(),e.y_root-self.root.winfo_y())
    def drag(self,e):
        if self.drag_start:
            self.root.geometry('+%d+%d'%(e.x_root-self.drag_start[0],e.y_root-self.drag_start[1]))
    def toggle_visible(self):
        if self.root.state()=='withdrawn': self.root.deiconify()
        else: self.root.withdraw()
    def toggle_lock(self):
        # On Windows, WS_EX_TRANSPARENT makes the window click-through.
        # Keep a keyboard escape: Ctrl+Shift+U is registered separately by Windows when locked.
        if not __import__('sys').platform.startswith('win'):
            self.status.config(text='Click-through supported on Windows only')
            return
        import ctypes
        hwnd=self.root.winfo_id()
        GWL_EXSTYLE=-20; WS_EX_LAYERED=0x80000; WS_EX_TRANSPARENT=0x20
        get=ctypes.windll.user32.GetWindowLongW; put=ctypes.windll.user32.SetWindowLongW
        style=get(hwnd,GWL_EXSTYLE)
        self.locked=not self.locked
        put(hwnd,GWL_EXSTYLE, (style|WS_EX_LAYERED|WS_EX_TRANSPARENT) if self.locked else (style & ~WS_EX_TRANSPARENT))
        self.lock_btn.config(text='Click-through: '+('ON' if self.locked else 'OFF'))
        if self.locked:
            self.status.config(text='Click-through ON • Ctrl+Shift+U unlocks')
            threading.Thread(target=self.unlock_hotkey,daemon=True).start()
    def unlock_hotkey(self):
        # Poll only while locked, no injection or interaction with game memory.
        import ctypes
        user32=ctypes.windll.user32
        while self.running and self.locked:
            ctrl=(user32.GetAsyncKeyState(0x11)&0x8000)!=0
            shift=(user32.GetAsyncKeyState(0x10)&0x8000)!=0
            u=(user32.GetAsyncKeyState(0x55)&0x8000)!=0
            if ctrl and shift and u:
                self.q.put(('unlock',None)); break
            time.sleep(.08)
    def render(self,players):
        for child in self.teams.winfo_children(): child.destroy()
        for team,color in ((0,BLUE),(1,ORANGE)):
            tk.Label(self.teams,text=('BLUE TEAM' if team==0 else 'ORANGE TEAM'),bg=BG,fg=color,font=('Segoe UI',10,'bold')).pack(anchor='w',pady=(9,3))
            members=[p for p in players if p.get('TeamNum')==team]
            if not members:
                tk.Label(self.teams,text='Waiting for players…',bg=BG,fg='#9ca3af',font=('Segoe UI',9)).pack(anchor='w')
            for p in members[:4]:
                name=str(p.get('Name','Unknown'))[:24]
                boost=p.get('Boost')
                valid=isinstance(boost,(int,float)) and not isinstance(boost,bool) and 0<=boost<=100
                val=round(boost) if valid else None
                row=tk.Frame(self.teams,bg=BG)
                row.pack(fill='x',pady=(3,1))
                tk.Label(row,text=name,bg=BG,fg='white',font=('Segoe UI',9),anchor='w').pack(side='left')
                tk.Label(row,text=(f'{val}%' if valid else 'N/A'),bg=BG,fg=color if valid else '#9ca3af',font=('Segoe UI',9,'bold')).pack(side='right')
                track=tk.Canvas(self.teams,height=7,bg='#374151',highlightthickness=0)
                track.pack(fill='x')
                if valid:
                    track.bind('<Configure>',lambda e,v=val,c=color,w=track:w.create_rectangle(0,0,e.width*v/100,7,fill=c,outline=''))
    def reader(self):
        if websocket is None:
            self.q.put(('status','Missing websocket-client: pip install -r requirements.txt'))
            return
        while self.running:
            try:
                self.q.put(('status','Connecting to '+URL))
                ws=websocket.create_connection(URL,timeout=3)
                ws.settimeout(2)
                self.q.put(('connected',True))
                while self.running:
                    try: raw=ws.recv()
                    except websocket.WebSocketTimeoutException: continue
                    if not raw: break
                    try: msg=json.loads(raw)
                    except (ValueError,TypeError): continue
                    if msg.get('Event')=='UpdateState':
                        data=msg.get('Data') or {}
                        if isinstance(data.get('Players'),list):
                            self.q.put(('players',data['Players']))
                ws.close()
            except Exception:
                pass
            self.q.put(('connected',False))
            for _ in range(20):
                if not self.running:return
                time.sleep(.1)
    def poll(self):
        latest=None
        while True:
            try: kind,value=self.q.get_nowait()
            except queue.Empty: break
            if kind=='players':latest=value
            elif kind=='connected':
                self.connected=value
                self.status.config(text='Connected • waiting for match' if value else 'Offline • enable Stats API, then start RL')
                if not value: self.render([])
            elif kind=='status':self.status.config(text=value)
            elif kind=='unlock' and self.locked:self.toggle_lock()
        if latest is not None:
            self.last_update=time.monotonic()
            self.status.config(text='LIVE • Official Rocket League Stats API')
            self.render(latest)
        if self.connected and self.last_update and time.monotonic()-self.last_update>5:
            self.status.config(text='Connected • no recent match updates')
            self.render([])
            self.last_update=0
        if self.running:self.root.after(100,self.poll)
    def close(self):
        self.running=False
        self.root.destroy()
    def run(self):self.root.mainloop()

if __name__=='__main__': HUD().run()
