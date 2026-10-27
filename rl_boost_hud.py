                    except ValueError:
                        if len(buf) > 4_000_000:
                            buf = ""  # corrupt stream, resync
                        break  # incomplete object, wait for more bytes
                    buf = buf[idx:]
                    self.handle(msg)

    def read_ws(self, port):
        ws = websocket.create_connection(f"ws://{HOST}:{port}", timeout=3)
        try:
            ws.settimeout(2)
            self.q.put(("connected", True))
            self.q.put(("status", f"Connected (ws :{port}) - waiting for match"))
            while self.running:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                if not raw:
                    raise ConnectionError("server closed connection")
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    self.q.put(("event", "Non-JSON message"))
                    continue
                self.handle(msg)
        finally:
            try:
                ws.close()
            except Exception:
                pass

    def handle(self, msg):
        self.q.put(("message", None))
        if not isinstance(msg, dict):
            self.q.put(("event", "Unexpected JSON format"))
            return

        event = msg.get("Event", "Unknown")
        data = msg.get("Data")
        if isinstance(data, str):  # some builds double-encode Data
            try:
                data = json.loads(data)
            except ValueError:
                data = None

        self.q.put(("event", str(event)))

        if event == "UpdateState" and isinstance(data, dict):
            players = data.get("Players")
            if isinstance(players, list):
                self.q.put(("players", players))
        elif event in ("MatchDestroyed", "MatchEnded"):
            self.q.put(("players", []))

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

