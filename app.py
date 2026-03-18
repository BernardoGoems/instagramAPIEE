import os
import re
import threading
import traceback


def _redact(text):
    """Remove access_token da mensagem de erro antes de exibir."""
    return re.sub(r'access_token=[^&\s"\']+', 'access_token=***', text)

from flask import Flask, send_file, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "dashboard.html")
_lock     = threading.Lock()
_last_error = ""


def refresh_data():
    """Coleta dados do Instagram e regenera o dashboard HTML."""
    global _last_error
    with _lock:
        try:
            print("Atualizando dados do Instagram...", flush=True)
            from coletar_dados import main as coletar
            from gerar_dashboard import gerar_dashboard
            coletar()
            gerar_dashboard(
                dados_path=os.path.join(BASE_DIR, "dados_instagram.json"),
                output_path=HTML_FILE,
            )
            _last_error = ""
            print("Dashboard atualizado com sucesso.", flush=True)
        except Exception as e:
            _last_error = _redact(traceback.format_exc())
            print(f"Erro ao atualizar dados:\n{_last_error}", flush=True)


LOADING_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="10">
<title>Carregando Dashboard...</title>
<link rel="icon" type="image/png" href="/static/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Fira+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Fira Sans', sans-serif;
    background: #020817; color: #94A3B8;
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 100vh; padding: 24px;
  }}
  .spinner {{
    width: 40px; height: 40px;
    border: 3px solid #0F172A;
    border-top-color: #FF6C00;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 24px;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  h2 {{
    font-family: 'Fira Code', monospace;
    color: #FF6C00; font-size: 1rem; font-weight: 600;
    letter-spacing: 0.5px; margin-bottom: 8px;
  }}
  p  {{ color: #64748B; font-size: 0.875rem; }}
  pre {{
    background: #0F172A; border: 1px solid #1E293B; border-radius: 8px;
    padding: 16px; color: #EF4444; font-family: 'Fira Code', monospace;
    font-size: 0.78rem; max-width: 800px; white-space: pre-wrap;
    margin-top: 24px; width: 100%;
  }}
</style>
</head>
<body>
  <div class="spinner"></div>
  <h2>Coletando dados do Instagram...</h2>
  <p>Esta página recarrega automaticamente a cada 10 segundos.</p>
  {error_block}
</body>
</html>"""


@app.route("/")
def index():
    if not os.path.exists(HTML_FILE):
        error_block = f"<pre>{_last_error}</pre>" if _last_error else ""
        return LOADING_PAGE.format(error_block=error_block), 503
    return send_file(HTML_FILE)


REFRESH_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Atualizando Dashboard...</title>
<link rel="icon" type="image/png" href="/static/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Fira+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Fira Sans', sans-serif;
    background: #020817; color: #94A3B8;
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 100vh; padding: 24px; gap: 0;
  }
  .spinner {
    width: 44px; height: 44px;
    border: 3px solid #0F172A;
    border-top-color: #FF6C00;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 28px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  h2 {
    font-family: 'Fira Code', monospace;
    color: #FF6C00; font-size: 1rem; font-weight: 600;
    letter-spacing: 0.5px; margin-bottom: 10px;
  }
  p { color: #64748B; font-size: 0.875rem; margin-bottom: 6px; }
  .countdown {
    font-family: 'Fira Code', monospace;
    font-size: 2rem; font-weight: 700;
    color: #FF6C00; margin: 20px 0 8px;
    text-shadow: 0 0 20px rgba(255,108,0,0.3);
  }
  .bar-track {
    width: 240px; height: 3px;
    background: #0F172A; border-radius: 2px; overflow: hidden; margin-top: 24px;
  }
  .bar-fill {
    height: 100%; width: 100%;
    background: linear-gradient(90deg, #072F58, #FF6C00);
    border-radius: 2px;
    animation: shrink 30s linear forwards;
  }
  @keyframes shrink { from { width: 100%; } to { width: 0%; } }
  .back-link {
    margin-top: 32px;
    font-size: 0.8rem; color: #334155;
    text-decoration: none; border-bottom: 1px solid #1E293B;
    transition: color 0.15s;
  }
  .back-link:hover { color: #64748B; }
</style>
<script>
  var secs = 30;
  function tick() {
    document.getElementById('cd').textContent = secs + 's';
    if (secs <= 0) { window.location.href = '/'; return; }
    secs--;
    setTimeout(tick, 1000);
  }
  window.onload = tick;
</script>
</head>
<body>
  <div class="spinner"></div>
  <h2>Atualizando dados do Instagram</h2>
  <p>Coletando métricas e regenerando o dashboard...</p>
  <div class="countdown" id="cd">30s</div>
  <p>Redirecionando automaticamente</p>
  <div class="bar-track"><div class="bar-fill"></div></div>
  <a href="/" class="back-link">Voltar agora</a>
</body>
</html>"""


@app.route("/refresh")
def refresh_manual():
    threading.Thread(target=refresh_data, daemon=True).start()
    return REFRESH_PAGE


@app.route("/status")
def status():
    return jsonify({
        "dashboard_exists": os.path.exists(HTML_FILE),
        "last_error": _last_error or None,
        "token_set": bool(os.environ.get("INSTAGRAM_ACCESS_TOKEN")),
    })


# Coleta inicial + agendamento — roda tanto com `python app.py` quanto com gunicorn
def _start_scheduler():
    threading.Thread(target=refresh_data, daemon=True).start()
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_data, "interval", hours=6)
    scheduler.start()

_start_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
