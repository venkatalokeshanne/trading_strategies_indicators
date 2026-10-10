"""Minimal stdio MCP client for Foresight.exe --mcp."""
import json, subprocess, sys, threading, queue
EXE = r"C:\Program Files\Foresight\Foresight.exe"
class FS:
    def __init__(self, port=None):
        import os
        env = dict(os.environ)
        if port: env["FORESIGHT_MCP_PORT"] = str(port); env["FORESIGHT_MCP_AUTOSTART"] = "0"
        self.p = subprocess.Popen([EXE, "--mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        self.q = queue.Queue(); self.id = 0
        threading.Thread(target=self._rd, daemon=True).start()
        self.req("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "claude-fs", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    def _rd(self):
        for line in self.p.stdout:
            try: self.q.put(json.loads(line))
            except Exception: pass
    def _send(self, m): self.p.stdin.write((json.dumps(m) + "\n").encode()); self.p.stdin.flush()
    def req(self, method, params=None, timeout=300):
        self.id += 1; i = self.id; self._send({"jsonrpc": "2.0", "id": i, "method": method, "params": params or {}})
        while True:
            m = self.q.get(timeout=timeout)
            if m.get("id") == i: return m
    def call(self, name, args=None, timeout=300):
        r = self.req("tools/call", {"name": name, "arguments": args or {}}, timeout)
        if "error" in r: return {"error": r["error"]}
        res = r["result"]
        if res.get("structuredContent") is not None: return res["structuredContent"]
        txt = "\n".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        try: return json.loads(txt)
        except Exception: return txt
if __name__ == "__main__":
    fs = FS(); tools = fs.req("tools/list")["result"]["tools"]
    print(len(tools), "tools")
    for t in tools: print("-", t["name"], ":", t["description"].split("\n")[0][:110])
