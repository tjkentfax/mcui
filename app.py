import os, signal, subprocess
from pathlib import Path
from flask import Flask, request, redirect, session, render_template_string, abort

BASE = Path("/home/minecraft").resolve()
START = (BASE / "start.sh").resolve()
PASSWORD = os.environ.get("MCUI_PASSWORD", "changeme")
SECRET = os.environ.get("MCUI_SECRET", "change-this-secret")

app = Flask(__name__)
app.secret_key = SECRET
proc = None

PAGE = r"""<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>mcui</title>
<style>
body{font-family:system-ui;margin:0;background:#101114;color:#eee}
header{padding:18px 24px;background:#191b20;display:flex;justify-content:space-between;align-items:center}
main{max-width:1100px;margin:24px auto;padding:0 16px}
.card{background:#191b20;border-radius:14px;padding:18px;margin-bottom:18px}
button,input{font:inherit}button{padding:9px 14px;border:0;border-radius:9px;cursor:pointer}
.start{background:#287a3e;color:#fff}.stop,.delete{background:#b33;color:#fff}
.drop{border:2px dashed #555;border-radius:12px;padding:35px;text-align:center}
.drop.over{border-color:#aaa;background:#222}
.row{display:flex;align-items:center;gap:10px;padding:10px;border-bottom:1px solid #2c2e33}
.row a{color:#eee;text-decoration:none;flex:1}
.path{margin-bottom:12px;color:#aaa}
small{color:#999}
</style></head>
<body><header><b>mcui</b><span>{{ "RUNNING" if running else "STOPPED" }}</span></header>
<main>
<div class="card">
<form method="post" action="/start" style="display:inline"><button class="start">Start server</button></form>
<form method="post" action="/stop" style="display:inline"><button class="stop">Stop server</button></form>
</div>
<div class="card">
<div class="path">/home/minecraft/{{ path }}</div>
<div id="drop" class="drop">Drag files here to upload<br><small>or choose files</small><br><br>
<input id="files" type="file" multiple></div>
<br>
{% if parent is not none %}<div class="row"><a href="/?path={{parent|urlencode}}">⬅️ ..</a></div>{% endif %}
{% for x in entries %}
<div class="row">
{% if x.dir %}📁 <a href="/?path={{x.rel|urlencode}}">{{x.name}}/</a>
{% else %}📄 <a href="/download?path={{x.rel|urlencode}}">{{x.name}}</a>
<form method="post" action="/delete"><input type="hidden" name="path" value="{{x.rel}}"><button class="delete">Delete</button></form>{% endif %}
</div>
{% endfor %}
</div>
</main>
<script>
const drop=document.getElementById('drop'), input=document.getElementById('files');
async function upload(fs){
 const path=new URLSearchParams(location.search).get('path')||'';
 for(const f of fs){const d=new FormData();d.append('file',f);d.append('path',path);
  const r=await fetch('/upload',{method:'POST',body:d}); if(!r.ok) alert(await r.text());
 }
 location.reload();
}
input.onchange=()=>upload(input.files);
['dragenter','dragover'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('over')}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('over')}));
drop.addEventListener('drop',ev=>upload(ev.dataTransfer.files));
</script></body></html>"""

LOGIN = r"""<!doctype html><html><body style="font-family:system-ui;max-width:400px;margin:80px auto;padding:20px;background:#101114;color:#eee">
<h1>mcui</h1><form method="post"><input name="password" type="password" placeholder="Password" autofocus style="padding:12px;width:100%;box-sizing:border-box"><button style="margin-top:12px;padding:12px;width:100%">Login</button></form></body></html>"""

def safe(rel=""):
    p=(BASE / rel).resolve()
    if p != BASE and BASE not in p.parents: abort(403)
    return p

@app.before_request
def auth():
    if request.endpoint != "login" and not session.get("ok"): return redirect("/login")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST" and request.form.get("password")==PASSWORD:
        session["ok"]=True; return redirect("/")
    return render_template_string(LOGIN)

@app.get("/")
def index():
    rel=request.args.get("path","").strip("/")
    p=safe(rel)
    if not p.is_dir(): abort(404)
    entries=[]
    for x in sorted(p.iterdir(), key=lambda z:(not z.is_dir(), z.name.lower())):
        entries.append({"name":x.name,"dir":x.is_dir(),"rel":str(x.relative_to(BASE))})
    parent=None if p==BASE else str(p.parent.relative_to(BASE))
    return render_template_string(PAGE,path=rel,running=proc is not None and proc.poll() is None,entries=entries,parent=parent)

@app.post("/start")
def start():
    global proc
    if proc is None or proc.poll() is not None:
        proc=subprocess.Popen(["/bin/sh",str(START)],cwd=BASE,stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    return redirect("/")

@app.post("/stop")
def stop():
    if proc is not None and proc.poll() is None: os.killpg(proc.pid,signal.SIGTERM)
    return redirect("/")

@app.post("/upload")
def upload():
    f=request.files.get("file")
    if not f or not f.filename: abort(400)
    rel=request.form.get("path","")
    dest=safe(rel)/Path(f.filename).name
    dest.parent.mkdir(parents=True,exist_ok=True)
    f.save(dest)
    return "ok"

@app.get("/download")
def download():
    from flask import send_file
    p=safe(request.args.get("path",""))
    if not p.is_file(): abort(404)
    return send_file(p)

@app.post("/delete")
def delete():
    p=safe(request.form.get("path",""))
    if p == BASE or not p.is_file(): abort(400)
    if p.suffix.lower() != ".jar": abort(400, "Only .jar files can be deleted.")
    p.unlink()
    return redirect(request.referrer or "/")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=8080)
