import json, random, string, time, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HOST="0.0.0.0"
PORT=8000
MAX_PLAYERS=12
rooms={}
lock=threading.Lock()

def code():
    while True:
        c="".join(random.choice(string.ascii_uppercase+string.digits) for _ in range(5))
        if c not in rooms:return c

def send(h,status,data,ctype="application/json"):
    raw=data if isinstance(data,bytes) else (json.dumps(data).encode() if ctype=="application/json" else data.encode())
    h.send_response(status);h.send_header("Content-Type",ctype+"; charset=utf-8")
    h.send_header("Cache-Control","no-store");h.send_header("Access-Control-Allow-Origin","*")
    h.send_header("Content-Length",str(len(raw)));h.end_headers();h.wfile.write(raw)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a):pass

    def body(self):
        n=int(self.headers.get("Content-Length","0"))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u=urlparse(self.path)
        if u.path=="/api/ping":
            return send(self,200,{"ok":True})
        if u.path=="/api/rooms":
            with lock:
                out=[{"code":c,"name":r["name"],"players":len(r["players"]),"maxPlayers":MAX_PLAYERS} for c,r in rooms.items()]
            return send(self,200,{"rooms":out})
        if u.path=="/api/state":
            q=parse_qs(u.query);c=q.get("code",[""])[0];pid=q.get("id",[""])[0]
            with lock:
                r=rooms.get(c)
                if not r or pid not in r["players"]:return send(self,404,{"error":"Sala ou jogador inválido"})
                now=time.time()
                r["players"][pid]["last"]=now
                players={k:{x:v for x,v in p.items() if x!="last"} for k,p in r["players"].items()}
            return send(self,200,{"players":players})
        if u.path=="/":
            return self.file("index.html")
        if u.path in ("/index.html","/style.css","/script.js"):
            return self.file(u.path[1:])
        return send(self,404,{"error":"Não encontrado"})

    def file(self,name):
        try:
            with open(name,"rb") as f:data=f.read()
            typ="text/html" if name.endswith(".html") else ("text/css" if name.endswith(".css") else "text/javascript")
            return send(self,200,data,typ)
        except FileNotFoundError:return send(self,404,b"Arquivo não encontrado","text/plain")

    def do_POST(self):
        u=urlparse(self.path)
        try:d=self.body()
        except:return send(self,400,{"error":"JSON inválido"})

        if u.path=="/api/create":
            with lock:
                c=code();name=str(d.get("name","Jogador"))[:16]
                rooms[c]={"name":name+"'s Room","created":time.time(),"players":{}}
            return send(self,200,{"code":c})

        if u.path=="/api/join":
            c=str(d.get("code","")).upper();name=str(d.get("name","Jogador"))[:16] or "Jogador"
            with lock:
                r=rooms.get(c)
                if not r:return send(self,404,{"error":"Sala não existe"})
                if len(r["players"])>=MAX_PLAYERS:return send(self,409,{"error":"Sala cheia"})
                pid="".join(random.choice(string.ascii_letters+string.digits) for _ in range(16))
                r["players"][pid]={"name":name,"x":random.randint(80,700),"y":random.randint(80,500),"hp":100,"score":0,"last":time.time()}
            return send(self,200,{"id":pid,"x":r["players"][pid]["x"],"y":r["players"][pid]["y"]})

        if u.path=="/api/update":
            c=str(d.get("code","")).upper();pid=str(d.get("id",""))
            with lock:
                r=rooms.get(c)
                if not r or pid not in r["players"]:return send(self,404,{"error":"Sala ou jogador inválido"})
                p=r["players"][pid]
                p["x"]=float(d.get("x",p["x"]));p["y"]=float(d.get("y",p["y"]))
                p["hp"]=int(d.get("hp",p["hp"]));p["score"]=int(d.get("score",p["score"]))
                p["last"]=time.time()
            return send(self,200,{"ok":True})

        if u.path=="/api/leave":
            c=str(d.get("code","")).upper();pid=str(d.get("id",""))
            with lock:
                r=rooms.get(c)
                if r:r["players"].pop(pid,None)
            return send(self,200,{"ok":True})
        return send(self,404,{"error":"Rota não encontrada"})

def cleanup():
    while True:
        time.sleep(5);now=time.time()
        with lock:
            for c in list(rooms):
                r=rooms[c]
                for pid in list(r["players"]):
                    if now-r["players"][pid]["last"]>10:r["players"].pop(pid,None)
                if not r["players"] and now-r["created"]>60:rooms.pop(c,None)

threading.Thread(target=cleanup,daemon=True).start()
print("======================================")
print("          ARENA.IO ONLINE")
print("======================================")
print("Abra: http://localhost:8000")
print("Na mesma rede, use o IP deste PC:")
print("http://IP-DO-PC:8000")
print("CTRL+C encerra o servidor.")
print("======================================")
ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
