
import json
import queue
import threading
import time
import tkinter as tk

try:
    import websocket
except ImportError:
    websocket = None

URL = "ws://127.0.0.1:49124"
BG = "#111827"
BLUE = "#60a5fa"
ORANGE = "#fb923c"


class HUD:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RL Boost HUD")
        self.root.geometry("310x440+1100+150")
        self.root.configure(bg=BG)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)

        self.q = queue.Queue()
        self.running = True
        self.connected = False
        self.last_update = 0
        self.last_error = "No connection attempted yet"
        self.messages = 0

        tk.Label(
            self.root,
            text="RL BOOST HUD",
            bg=BG,
            fg="white",
            font=("Segoe UI", 15, "bold")
        ).pack(pady=(12, 5))

        self.status = tk.Label(
            self.root,
            text="Starting...",
            bg=BG,
            fg="#d1d5db",
            font=("Segoe UI", 9),
            wraplength=290
        )
        self.status.pack(padx=10)

        self.details = tk.Label(
            self.root,
            text="Waiting for diagnostics...",
            bg=BG,
            fg="#fbbf24",
            font=("Segoe UI", 9),
            wraplength=290,
            justify="left"
        )
        self.details.pack(padx=10, pady=8)

        self.teams = tk.Frame(self.root, bg=BG)
        self.teams.pack(fill="both", expand=True, padx=12)

        tk.Button(
            self.root,
            text="Close HUD",
            command=self.close
        ).pack(pady=10)

        self.render([])
        self.root.after(100, self.poll)
        threading.Thread(target=self.reader, daemon=True).start()

    def render(self, players):
        for child in self.teams.winfo_children():
            child.destroy()

        for team, color in ((0, BLUE), (1, ORANGE)):
            title = "BLUE TEAM" if team == 0 else "ORANGE TEAM"

            tk.Label(
                self.teams,
                text=title,
                bg=BG,
                fg=color,
                font=("Segoe UI", 11, "bold")
            ).pack(anchor="w", pady=(10, 4))

            members = [
                p for p in players
                if isinstance(p, dict) and p.get("TeamNum") == team
            ]

            if not members:
                tk.Label(
                    self.teams,
                    text="Waiting for players...",
                    bg=BG,
                    fg="#9ca3af"
                ).pack(anchor="w")

            for player in members[:4]:
                name = str(player.get("Name", "Unknown"))[:20]
                boost = player.get("Boost")

                valid = (
                    isinstance(boost, (int, float))
                    and not isinstance(boost, bool)
                    and 0 <= boost <= 100
                )

                value = f"{round(boost)}%" if valid else "N/A"

                row = tk.Frame(self.teams, bg=BG)
                row.pack(fill="x", pady=3)

                tk.Label(
                    row,
                    text=name,
                    bg=BG,
                    fg="white"
                ).pack(side="left")

                tk.Label(
                    row,
                    text=value,
                    bg=BG,
                    fg=color,
                    font=("Segoe UI", 10, "bold")
                ).pack(side="right")

    def reader(self):
        if websocket is None:
            self.q.put(("error", "websocket-client is missing"))
            return

        while self.running:
            ws = None

            try:
                self.q.put(("status", "Connecting..."))

                ws = websocket.create_connection(
                    URL,
                    timeout=3,
                    http_proxy_host=None,
                    http_proxy_port=None
                )
                ws.settimeout(2)

                self.q.put(("connected", True))
                self.q.put(("status", "Connected - waiting for match"))

                while self.running:
                    try:
                        raw = ws.recv()
                    except websocket.WebSocketTimeoutException:
                        continue

                    if not raw:
                        self.q.put(("error", "Server closed connection"))
                        break

                    self.q.put(("message", None))

                    try:
                        msg = json.loads(raw)
                    except (ValueError, TypeError):
                        self.q.put(("event", "Non-JSON message"))
                        continue

                    if not isinstance(msg, dict):
                        self.q.put(("event", "Unexpected JSON format"))
                        continue

                    event = msg.get("Event", "Unknown")
self.q.put(("event", str(event)))
if event == "UpdateState":
    self.q.put(("event", "UpdateState keys: " + str(list((msg.get("Data") or {}).keys()))))

                    if event == "UpdateState":
                        data = msg.get("Data") or {}

                        if isinstance(data, dict):
                            players = data.get("Players")

                            if isinstance(players, list):
                                self.q.put(("players", players))

            except Exception as e:
                self.q.put(("error", str(e)))

            finally:
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass

                self.q.put(("connected", False))

            for _ in range(20):
                if not self.running:
                    return
                time.sleep(0.1)

    def poll(self):
        latest_players = None

        while True:
            try:
                kind, value = self.q.get_nowait()
            except queue.Empty:
                break

            if kind == "connected":
                self.connected = value
                self.status.config(
                    text="Connected" if value else "Disconnected"
                )

                if not value:
                    self.render([])

            elif kind == "status":
                self.status.config(text=value)

            elif kind == "error":
                self.last_error = value
                self.details.config(
                    text="LAST ERROR:\n" + value
                )

            elif kind == "message":
                self.messages += 1

            elif kind == "event":
                self.details.config(
                    text=(
                        f"Messages: {self.messages}\n"
                        f"Last event: {value}\n"
                        f"Last error: {self.last_error}"
                    )
                )

            elif kind == "players":
                latest_players = value

        if latest_players is not None:
            self.last_update = time.monotonic()
            self.status.config(text="LIVE - receiving player data")
            self.render(latest_players)

        if (
            self.connected
            and self.last_update
            and time.monotonic() - self.last_update > 5
        ):
            self.status.config(text="Connected - no recent updates")
            self.render([])
            self.last_update = 0

        if self.running:
            self.root.after(100, self.poll)

    def close(self):
        self.running = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    HUD().run()

