# Render port probe: kya UDP 53 bind hota hai, bahar jaata hai, andar aata hai?
# Render pe Web Service bana ke start command: python probe.py
# Phir browser mein https://TERA-APP.onrender.com/ kholo (report JSON dikhegi)
import os, json, socket, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORTS = [53, 5300, 10001]
res = {"uid": os.getuid(), "bind": {}, "udp_received": {}, "outbound": {}}
lock = threading.Lock()

def listen(p):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", p))
        res["bind"][str(p)] = "OK"
    except Exception as e:
        res["bind"][str(p)] = "FAIL: %s" % e
        return
    res["udp_received"][str(p)] = 0
    while True:
        d, a = s.recvfrom(4096)
        with lock:
            res["udp_received"][str(p)] += 1
        s.sendto(d, a)  # echo

def outbound():
    t = time.time()
    try:
        ip = urllib.request.urlopen("https://api.ipify.org", timeout=10).read().decode()
        res["outbound"]["public_ip_(outbound)"] = ip
    except Exception as e:
        res["outbound"]["public_ip_(outbound)"] = "FAIL: %s" % e
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(5)
        q = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01"
        s.sendto(q, ("8.8.8.8", 53)); s.recvfrom(512)
        res["outbound"]["udp53_to_8.8.8.8"] = "OK"
    except Exception as e:
        res["outbound"]["udp53_to_8.8.8.8"] = "FAIL: %s" % e
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5).close()
        res["outbound"]["tcp53_to_8.8.8.8"] = "OK"
    except Exception as e:
        res["outbound"]["tcp53_to_8.8.8.8"] = "FAIL: %s" % e

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        with lock:
            b = json.dumps(res, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

if __name__ == "__main__":
    for p in PORTS:
        threading.Thread(target=listen, args=(p,), daemon=True).start()
    threading.Thread(target=outbound, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), H).serve_forever()
