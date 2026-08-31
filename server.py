import json
import random
import string
import time
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HOST = "0.0.0.0"
PORT = 8000
MAX_PLAYERS = 12

rooms = {}
lock = threading.Lock()


def new_code():
    while True:
        code = "".join(
            random.choice(string.ascii_uppercase + string.digits)
            for _ in range(5)
        )

        if code not in rooms:
            return code


def send_json(handler, status, data):
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")

    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()

    handler.wfile.write(raw)


class ArenaServer(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def read_json(self):
        size = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(size)

        if not data:
            return {}

        return json.loads(data)

    # =========================
    # GET
    # =========================

    def do_GET(self):

        url = urlparse(self.path)

        # Teste de ping
        if url.path == "/api/ping":
            return send_json(self, 200, {
                "ok": True
            })

        # Lista de salas
        if url.path == "/api/rooms":

            with lock:

                room_list = []

                for code, room in rooms.items():

                    room_list.append({
                        "code": code,
                        "name": room["name"],
                        "players": len(room["players"]),
                        "maxPlayers": MAX_PLAYERS
                    })

            return send_json(self, 200, {
                "rooms": room_list
            })

        # Estado da sala
        if url.path == "/api/state":

            query = parse_qs(url.query)

            code = query.get("code", [""])[0].upper()
            player_id = query.get("id", [""])[0]

            with lock:

                room = rooms.get(code)

                if not room:
                    return send_json(self, 404, {
                        "error": "Sala nao existe"
                    })

                if player_id not in room["players"]:
                    return send_json(self, 404, {
                        "error": "Jogador nao encontrado"
                    })

                room["players"][player_id]["last"] = time.time()

                players = {}

                for pid, player in room["players"].items():

                    players[pid] = {
                        "name": player["name"],
                        "x": player["x"],
                        "y": player["y"],
                        "hp": player["hp"],
                        "score": player["score"]
                    }

            return send_json(self, 200, {
                "players": players
            })

        # Arquivos do jogo
        files = {
            "/": "index.html",
            "/index.html": "index.html",
            "/style.css": "style.css",
            "/script.js": "script.js"
        }

        if url.path in files:

            filename = files[url.path]

            try:

                with open(filename, "rb") as file:
                    content = file.read()

                if filename.endswith(".html"):
                    content_type = "text/html"

                elif filename.endswith(".css"):
                    content_type = "text/css"

                else:
                    content_type = "text/javascript"

                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    content_type + "; charset=utf-8"
                )
                self.send_header(
                    "Content-Length",
                    str(len(content))
                )
                self.end_headers()

                self.wfile.write(content)

                return

            except FileNotFoundError:

                return send_json(self, 404, {
                    "error": "Arquivo nao encontrado"
                })

        return send_json(self, 404, {
            "error": "Pagina nao encontrada"
        })

    # =========================
    # POST
    # =========================

    def do_POST():

        try:
            data = self.read_json()
        except:
            return send_json(self, 400, {
                "error": "JSON invalido"
            })

        # =====================
        # CRIAR SALA
        # =====================

        if self.path == "/api/create":

            name = str(
                data.get("name", "Jogador")
            ).strip()

            if not name:
                name = "Jogador"

            name = name[:16]

            with lock:

                code = new_code()

                rooms[code] = {
                    "name": name + "'s Room",
                    "created": time.time(),
                    "players": {}
                }

            return send_json(self, 200, {
                "code": code
            })

        # =====================
        # ENTRAR NA SALA
        # =====================

        if self.path == "/api/join":

            code = str(
                data.get("code", "")
            ).upper()

            name = str(
                data.get("name", "Jogador")
            ).strip()

            if not name:
                name = "Jogador"

            name = name[:16]

            with lock:

                room = rooms.get(code)

                if not room:

                    return send_json(self, 404, {
                        "error": "Sala nao existe"
                    })

                if len(room["players"]) >= MAX_PLAYERS:

                    return send_json(self, 409, {
                        "error": "Sala cheia"
                    })

                player_id = "".join(
                    random.choice(
                        string.ascii_letters + string.digits
                    )
                    for _ in range(16)
                )

                x = random.randint(100, 700)
                y = random.randint(100, 500)

                room["players"][player_id] = {

                    "name": name,

                    "x": x,
                    "y": y,

                    "hp": 100,
                    "score": 0,

                    "last": time.time()
                }

            return send_json(self, 200, {

                "id": player_id,

                "x": x,
                "y": y
            })

        # =====================
        # ATUALIZAR JOGADOR
        # =====================

        if self.path == "/api/update":

            code = str(
                data.get("code", "")
            ).upper()

            player_id = str(
                data.get("id", "")
            )

            with lock:

                room = rooms.get(code)

                if not room:

                    return send_json(self, 404, {
                        "error": "Sala nao existe"
                    })

                player = room["players"].get(player_id)

                if not player:

                    return send_json(self, 404, {
                        "error": "Jogador nao encontrado"
                    })

                player["x"] = float(
                    data.get("x", player["x"])
                )

                player["y"] = float(
                    data.get("y", player["y"])
                )

                player["hp"] = int(
                    data.get("hp", player["hp"])
                )

                player["score"] = int(
                    data.get("score", player["score"])
                )

                player["last"] = time.time()

            return send_json(self, 200, {
                "ok": True
            })

        # =====================
        # SAIR DA SALA
        # =====================

        if self.path == "/api/leave":

            code = str(
                data.get("code", "")
            ).upper()

            player_id = str(
                data.get("id", "")
            )

            with lock:

                room = rooms.get(code)

                if room:

                    room["players"].pop(
                        player_id,
                        None
                    )

            return send_json(self, 200, {
                "ok": True
            })

        return send_json(self, 404, {
            "error": "Rota nao encontrada"
        })


# =============================
# LIMPEZA DE JOGADORES
# =============================

def cleanup():

    while True:

        time.sleep(5)

        now = time.time()

        with lock:

            for code in list(rooms.keys()):

                room = rooms[code]

                for player_id in list(
                    room["players"].keys()
                ):

                    player = room["players"][player_id]

                    if now - player["last"] > 10:

                        del room["players"][player_id]

                # Apaga sala vazia depois de 60 segundos

                if (
                    not room["players"]
                    and now - room["created"] > 60
                ):

                    del rooms[code]


threading.Thread(
    target=cleanup,
    daemon=True
).start()


# =============================
# INICIAR SERVIDOR
# =============================

print("===================================")
print("          ARENA.IO ONLINE")
print("===================================")
print()
print("Servidor iniciado!")
print()
print("Abra no navegador:")
print("http://localhost:8000")
print()
print("CTRL+C para desligar.")
print("===================================")

server = ThreadingHTTPServer(
    (HOST, PORT),
    ArenaServer
)

server.serve_forever()