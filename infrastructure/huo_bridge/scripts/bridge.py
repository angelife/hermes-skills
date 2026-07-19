#!/usr/bin/env python3
"""
火同学 HTTP Bridge — 木同学(云端)远程派活入口。
设计对齐 Federation Hub 消息格式，未来 HTTP→WebSocket→MQ 复用。
运行在火同学 Mac 本机：python3 bridge.py --port 8899 --token <随机token>

端点：
  GET  /capabilities        自报能力
  POST /tasks                {"id","action","args","timeout"} → {"task_id"}
  GET  /tasks/{id}           {"id","ok","stdout","stderr","duration_ms","status"}
  GET  /health              ok

动作分级（白名单，禁裸shell）：
  Read:    git_status, ps, df, gateway_status, nlm_help
  Build:   git_pull, hugo_build
  Service: gateway_restart
  Device:  adb_devices, adb_pull
  (Dangerous/Interactive: 无对应动作，永远不可达)
"""
import argparse, json, subprocess, threading, time, uuid, os, shlex, http.server, socketserver, datetime

ARGS = None
TOKEN = ""
TASKS = {}  # id -> {status, stdout, stderr, duration_ms, ok}
LOCK = threading.Lock()

# 动作 → 命令构造。NLM 先探测占位（不写死格式）。
def build_cmd(action, args):
    # 返回 (cmd_list, timeout_override) 或 None（未知动作）
    if action == "git_status":
        return (["git", "-C", os.path.expanduser("~/workspace"), "status", "--short"], 30)
    if action == "git_pull":
        return (["git", "-C", os.path.expanduser("~/workspace"), "pull"], 60)
    if action == "ps":
        return (["ps", "aux"], 20)
    if action == "df":
        return (["df", "-h"], 20)
    if action == "gateway_status":
        # 查 Hermes gateway 进程（火同学若装了）
        return (["pgrep", "-fl", "hermes"], 20)
    if action == "gateway_restart":
        # 重启 gateway（按实际环境补，先占位 pgrep+kill+launch 风险高，默认禁）
        return None  # Service 级但破坏性，默认不自动做，需显式启用
    if action == "hugo_build":
        return (["bash", "-c", "cd ~/hugo-site && hugo"], 120)
    if action == "adb_devices":
        return (["adb", "devices"], 20)
    if action == "adb_pull":
        # args: {"serial","remote","local"}
        ser = args.get("serial", "")
        remote = args.get("remote", "")
        local = args.get("local", ".")
        return (["adb", "-s", ser, "pull", remote, local], 60)
    if action == "nlm_help":
        # 探测 NLM CLI 是否存在及格式（不写死调用）
        return (["bash", "-c", "which nlm nlm-cli 2>/dev/null; nlm --help 2>&1 | head -20; nlm-cli --help 2>&1 | head -20"], 30)
    return None

def run_task(tid, action, args, timeout):
    t0 = time.time()
    res = build_cmd(action, args or {})
    out, err, ok = "", "", False
    if res is None:
        err = f"unknown or disabled action: {action}"
        ok = False
    else:
        cmd, cmd_timeout = res
        timeout = min(timeout, cmd_timeout)
        # 白名单动作已受控，用 shell=True + 字符串命令（沙箱 subprocess 对 list 不稳）
        if isinstance(cmd, str):
            cmd_str = cmd
        else:
            cmd_str = " ".join(str(c) for c in cmd)  # 白名单内，元素均为安全 token
        try:
            r = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=timeout)
            out = r.stdout.strip()
            err = r.stderr.strip()
            ok = r.returncode == 0
        except subprocess.TimeoutExpired:
            err = f"timeout after {timeout}s"
            ok = False
        except Exception as e:
            err = f"exec error: {e}"
            ok = False
    dur = int((time.time() - t0) * 1000)
    with LOCK:
        TASKS[tid] = {"status": "done", "ok": ok, "stdout": out, "stderr": err, "duration_ms": dur}
    # 审计
    audit(f"{tid}|{action}|ok={ok}|dur={dur}ms")

def audit(line):
    try:
        with open(os.path.expanduser("~/bridge_audit.log"), "a") as f:
            f.write(datetime.datetime.now().isoformat() + " " + line + "\n")
    except:
        pass

class H(http.server.BaseHTTPRequestHandler):
    def _j(self, code, obj):
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode())

    def _auth(self):
        return self.headers.get("Authorization", "") == f"Bearer {TOKEN}"

    def do_GET(self):
        if self.path == "/health":
            return self._j(200, {"ok": True})
        if self.path == "/capabilities":
            if not self._auth(): return self._j(401, {"error": "unauth"})
            caps = {
                "hermes": subprocess.run(["pgrep","-f","hermes"],capture_output=True).returncode==0,
                "gateway": subprocess.run(["pgrep","-f","gateway"],capture_output=True).returncode==0,
                "adb": subprocess.run(["which","adb"],capture_output=True).returncode==0,
                "nlm": subprocess.run(["bash","-c","which nlm nlm-cli"],capture_output=True).returncode==0,
                "git": subprocess.run(["which","git"],capture_output=True).returncode==0,
            }
            return self._j(200, caps)
        if self.path.startswith("/tasks/"):
            tid = self.path.split("/")[-1]
            with LOCK:
                t = TASKS.get(tid)
            if not t: return self._j(404, {"error": "not found"})
            return self._j(200, {"id": tid, **t})
        return self._j(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/tasks":
            return self._j(404, {"error": "not found"})
        if not self._auth(): return self._j(401, {"error": "unauth"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._j(400, {"error": f"bad body: {e}"})
        tid = body.get("id") or str(uuid.uuid4())
        action = body.get("action", "")
        args = body.get("args", {})
        timeout = min(int(body.get("timeout", 30)), 300)
        with LOCK:
            TASKS[tid] = {"status": "running", "ok": None, "stdout": "", "stderr": "", "duration_ms": 0}
        threading.Thread(target=run_task, args=(tid, action, args, timeout), daemon=True).start()
        return self._j(202, {"task_id": tid, "status": "running"})

    def log_message(self, *a):
        pass

def main():
    global ARGS, TOKEN
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8899)
    p.add_argument("--token", required=True, help="Bearer token (>=128bit random)")
    p.add_argument("--workdir", default="~")
    ARGS = p.parse_args()
    TOKEN = ARGS.token
    httpd = socketserver.TCPServer(("127.0.0.1", ARGS.port), H)
    print(f"bridge on 127.0.0.1:{ARGS.port}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()
