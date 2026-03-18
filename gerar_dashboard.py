import json
from datetime import datetime
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _avg(lst):
    return round(sum(lst) / len(lst), 1) if lst else 0


def _parse_ts(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main function
# ─────────────────────────────────────────────────────────────────────────────

def gerar_dashboard(dados_path="dados_instagram.json", output_path="dashboard.html"):

    # ── Load data ─────────────────────────────────────────────────────────────
    with open(dados_path, encoding="utf-8") as f:
        dados = json.load(f)

    perfil         = dados["perfil"]
    posts          = dados["posts"]
    insights_conta = dados["insights_conta"]

    # ── Parse account-level insights ─────────────────────────────────────────
    metricas_dict = {}
    for metrica in insights_conta:
        nome = metrica["name"]
        if "values" in metrica:
            valores = [v["value"] for v in metrica.get("values", [])]
            datas   = [v["end_time"][:10] for v in metrica.get("values", [])]
            metricas_dict[nome] = {"valores": valores, "datas": datas}
        elif "total_value" in metrica:
            tv = metrica["total_value"]
            breakdowns = tv.get("breakdowns", [])
            if breakdowns:
                resultados = breakdowns[0].get("results", [])
                valores = [r.get("value", 0) for r in resultados]
                datas   = [r.get("dimension_values", [""])[0] for r in resultados]
            else:
                valores = [tv.get("value", 0)]
                datas   = ["total"]
            metricas_dict[nome] = {"valores": valores, "datas": datas}

    # ── Summary KPI cards ─────────────────────────────────────────────────────
    total_curtidas    = sum(p.get("like_count", 0) or 0 for p in posts)
    total_comentarios = sum(p.get("comments_count", 0) or 0 for p in posts)
    total_posts       = len(posts)
    engajamento_medio = (
        round((total_curtidas + total_comentarios) / total_posts, 1)
        if total_posts else 0
    )

    # ── Reach and follower series for JS embedding ────────────────────────────
    reach_vals  = metricas_dict.get("reach", {}).get("valores", [])
    reach_dates = metricas_dict.get("reach", {}).get("datas", [])
    reach_series_json = json.dumps([{"date": d, "value": v} for d, v in zip(reach_dates, reach_vals)])

    follower_vals  = metricas_dict.get("follower_count", {}).get("valores", [])
    follower_dates = metricas_dict.get("follower_count", {}).get("datas", [])
    followers_series_json = json.dumps([{"date": d, "value": v} for d, v in zip(follower_dates, follower_vals)])

    # ── Engagement by media type (initial, all posts) ─────────────────────────
    tipo_curtidas    = defaultdict(list)
    tipo_comentarios = defaultdict(list)
    for p in posts:
        t = p.get("media_type", "IMAGE")
        tipo_curtidas[t].append(p.get("like_count", 0) or 0)
        tipo_comentarios[t].append(p.get("comments_count", 0) or 0)

    tipos_labels          = list(tipo_curtidas.keys())
    tipos_avg_curtidas    = [_avg(tipo_curtidas[t])    for t in tipos_labels]
    tipos_avg_comentarios = [_avg(tipo_comentarios[t]) for t in tipos_labels]
    tipos_labels_json      = json.dumps(tipos_labels)
    tipos_curtidas_json    = json.dumps(tipos_avg_curtidas)
    tipos_comentarios_json = json.dumps(tipos_avg_comentarios)

    # ── Donut: distribution by media type ────────────────────────────────────
    tipo_count = defaultdict(int)
    for p in posts:
        tipo_count[p.get("media_type", "IMAGE")] += 1
    donut_labels = json.dumps(list(tipo_count.keys()))
    donut_data   = json.dumps(list(tipo_count.values()))

    # ── Top 5 by likes ────────────────────────────────────────────────────────
    top5          = sorted(posts, key=lambda p: p.get("like_count", 0) or 0, reverse=True)[:5]
    top5_labels   = json.dumps([(p.get("caption") or "sem legenda")[:30] for p in top5])
    top5_curtidas = json.dumps([p.get("like_count", 0) or 0 for p in top5])
    top5_links    = json.dumps([p.get("permalink", "#") or "#" for p in top5])

    # ── Timeline ──────────────────────────────────────────────────────────────
    posts_ordenados      = sorted(posts, key=lambda p: p.get("timestamp", ""))
    timeline_labels      = json.dumps([p.get("timestamp", "")[:10] for p in posts_ordenados])
    timeline_curtidas    = json.dumps([p.get("like_count", 0) or 0 for p in posts_ordenados])
    timeline_comentarios = json.dumps([p.get("comments_count", 0) or 0 for p in posts_ordenados])

    # ── Shares & Saved (last 10) ──────────────────────────────────────────────
    last10 = posts_ordenados[-10:]
    shares_salvos_labels  = json.dumps([p.get("timestamp", "")[:10][5:] for p in last10])
    shares_salvos_shares  = json.dumps([(p.get("insights", {}).get("shares", 0) or 0) for p in last10])
    shares_salvos_saved   = json.dumps([(p.get("insights", {}).get("saved", 0) or 0) for p in last10])

    # ── All posts as JSON for client-side JS (dashboard + analysis) ───────────
    posts_for_js = []
    for p in posts:
        ins  = p.get("insights", {})
        tipo = p.get("media_type", "IMAGE")
        img  = (p.get("thumbnail_url") or p.get("media_url") or "") if tipo in ("VIDEO", "REEL") \
               else (p.get("media_url") or p.get("thumbnail_url") or "")
        ts_full = p.get("timestamp") or ""
        hour = int(ts_full[11:13]) if len(ts_full) >= 13 else -1
        posts_for_js.append({
            "timestamp":      ts_full[:10],
            "like_count":     p.get("like_count", 0) or 0,
            "comments_count": p.get("comments_count", 0) or 0,
            "shares":         ins.get("shares", 0) or 0,
            "saved":          ins.get("saved", 0) or 0,
            "reach":          ins.get("reach", 0) or 0,
            "media_type":     tipo,
            "caption":        (p.get("caption") or "")[:30],
            "permalink":      p.get("permalink", "#") or "#",
            "img":            img,
            "hour":           hour,
        })
    posts_json = json.dumps(posts_for_js)

    # ── Posts table HTML ───────────────────────────────────────────────────────
    posts_html = ""
    for p in posts:
        ins        = p.get("insights", {})
        raw_cap    = p.get("caption") or ""
        caption    = (raw_cap[:60] + "…") if len(raw_cap) > 60 else (raw_cap or "—")
        data       = p.get("timestamp", "")[:10]
        tipo_raw   = p.get("media_type", "IMAGE")

        if tipo_raw in ("VIDEO", "REEL"):
            imagem = p.get("thumbnail_url") or p.get("media_url") or ""
        else:
            imagem = p.get("media_url") or p.get("thumbnail_url") or ""

        link        = p.get("permalink", "#")
        tipo        = tipo_raw
        curtidas    = ins.get("likes",              p.get("like_count", 0))
        comentarios = ins.get("comments",           p.get("comments_count", 0))
        alcance     = ins.get("reach",              "—")
        interacoes  = ins.get("total_interactions", "—")
        salvos      = ins.get("saved",              "—")
        views       = ins.get("views",              "—")

        posts_html += f"""
        <tr>
          <td><a href="{link}" target="_blank" rel="noopener"><img src="{imagem}" class="post-thumb" alt="Post thumbnail" loading="lazy" onerror="this.src='https://placehold.co/60x60/0F172A/FF6C00?text=?'"></a></td>
          <td class="caption-cell">{caption}</td>
          <td><span class="badge badge-{tipo.lower()}">{tipo}</span></td>
          <td>{data}</td>
          <td>{curtidas}</td>
          <td>{comentarios}</td>
          <td>{alcance}</td>
          <td>{interacoes}</td>
          <td>{salvos}</td>
          <td>{views}</td>
        </tr>"""

    # ── Last updated timestamp ─────────────────────────────────────────────────
    coletado_em = dados.get("coletado_em", "")[:16].replace("T", " ")

    # ── Followers count (embedded for JS analysis) ─────────────────────────────
    followers_count = perfil.get("followers_count", 1) or 1

    # ── Hashtags por área (estático, curado para a Engehall) ──────────────────
    hashtags_por_area_data = [
        {
            "area": "Elétrica", "cls": "eletrica",
            "tags": ["#eletricista", "#instalacaoeletrica", "#eletricidadepredial",
                     "#dicaseletrica", "#quadroeletrico", "#eletricadomestica",
                     "#instalacaoeletricaresidencial", "#eletristaresidencial",
                     "#eletricaindustrial", "#engehall"],
        },
        {
            "area": "Climatização", "cls": "climatizacao",
            "tags": ["#arcondicionado", "#climatizacao", "#instalacaoarcondicionado",
                     "#manutencaoar", "#inverter", "#splitinverter",
                     "#arcondicionadoinverter", "#higienizacaoar", "#refrigeracao"],
        },
        {
            "area": "Soluções Tecnológicas / LED", "cls": "tecnologia",
            "tags": ["#perfildeled", "#iluminacaoled", "#fitaled", "#iluminacaointerna",
                     "#ledbrasil", "#designdeinteriores", "#iluminacaodecorada",
                     "#sancaled", "#automacaoresidencial", "#smarthouse"],
        },
        {
            "area": "Cursos", "cls": "cursos",
            "tags": ["#cursoseletrica", "#eletricapredial", "#formacaoprofissional",
                     "#cursoonline", "#aprendaeletrica", "#qualificacaoprofissional",
                     "#ensinotecnico", "#cursoeletricaindustrial", "#engehall"],
        },
    ]
    hashtags_json = json.dumps(hashtags_por_area_data, ensure_ascii=False)

    # ─────────────────────────────────────────────────────────────────────────
    # HTML output
    # ─────────────────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="pt-BR" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script>(function(){{var t=localStorage.getItem('engehall_theme');if(t)document.documentElement.setAttribute('data-theme',t);}})();</script>
<title>Dashboard Instagram — @{perfil.get('username', 'engehalleletrica')}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">

<style>
  /* ── Design System: Engehall — OLED Dark + Orange #FF6C00 + Navy #072F58 ── */
  :root {{
    --bg:        #020817;
    --surface:   #0F172A;
    --surface2:  #1E293B;
    --border:    #1E293B;
    --border2:   #334155;
    --primary:   #3B82F6;
    --primary2:  #072F58;
    --accent:    #FF6C00;
    --accent-dim:rgba(255,108,0,0.12);
    --text:      #E2E8F0;
    --text-muted:#64748B;
    --text-sub:  #94A3B8;
    --green:     #10B981;
    --red:       #EF4444;
    --violet:    #8B5CF6;
    --c-grid:    rgba(30,41,59,0.8);
    --c-tick:    #334155;
    --radius:    12px;
    --radius-sm: 8px;
    --transition:150ms ease;
  }}

  /* ── Light mode overrides ── */
  [data-theme="light"] {{
    --bg:        #F8FAFC;
    --surface:   #FFFFFF;
    --surface2:  #F1F5F9;
    --border:    #E2E8F0;
    --border2:   #CBD5E1;
    --text:      #0F172A;
    --text-muted:#64748B;
    --text-sub:  #475569;
    --c-grid:    rgba(203,213,225,0.6);
    --c-tick:    #94A3B8;
  }}
  [data-theme="light"] header {{
    background: linear-gradient(135deg, #FFFFFF 0%, #F1F5F9 50%, #EFF6FF 100%);
    border-bottom-color: var(--border);
  }}
  [data-theme="light"] header::after {{
    background: linear-gradient(90deg, transparent 60%, rgba(7,47,88,0.04) 100%);
  }}
  [data-theme="light"] .tab-nav {{
    background: var(--surface);
    backdrop-filter: none;
  }}
  [data-theme="light"] .filter-sticky {{
    background: var(--surface);
    border-bottom-color: var(--border);
    backdrop-filter: none;
  }}
  [data-theme="light"] .card::before {{
    background: linear-gradient(135deg, rgba(255,108,0,0.04) 0%, transparent 100%);
  }}
  [data-theme="light"] .header-text h1 {{ color: #0F172A; }}
  [data-theme="light"] .rec-item {{
    background: var(--surface2);
    border-left-color: var(--primary2);
  }}
  [data-theme="light"] pre {{
    background: var(--surface2);
    border-color: var(--border);
    color: #DC2626;
  }}

  /* ── Reset & base ── */
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    font-family: 'Fira Sans', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    font-size: 16px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }}
  @media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{ transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }}
  }}

  /* ── Header ── */
  header {{
    background: linear-gradient(135deg, #020817 0%, #0F172A 50%, #0f1f3d 100%);
    border-bottom: 1px solid var(--border);
    position: relative;
    overflow: hidden;
  }}
  header::after {{
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent 60%, rgba(59,130,246,0.05) 100%);
    pointer-events: none;
  }}
  .header-inner {{
    max-width: 1280px;
    margin: 0 auto;
    padding: 24px 32px;
    display: flex;
    align-items: center;
    gap: 20px;
    position: relative; z-index: 1;
  }}
  .header-accent {{
    width: 4px; height: 56px;
    background: linear-gradient(180deg, var(--accent) 0%, var(--primary) 100%);
    border-radius: 2px;
    flex-shrink: 0;
    box-shadow: 0 0 12px rgba(255,108,0,0.4);
  }}
  header img {{
    width: 64px; height: 64px;
    border-radius: 50%;
    border: 2px solid var(--accent);
    object-fit: cover;
    flex-shrink: 0;
    box-shadow: 0 0 16px rgba(255,108,0,0.25);
  }}
  .header-text h1 {{
    font-family: 'Fira Code', monospace;
    font-size: 1.6rem; font-weight: 700;
    color: #FFFFFF; letter-spacing: -0.5px;
  }}
  .header-text h1 span {{ color: var(--accent); }}
  .header-text p {{ color: var(--text-sub); font-size: 0.875rem; margin-top: 2px; line-height: 1.5; }}
  .header-right {{ margin-left: auto; display: flex; align-items: center; gap: 12px; }}
  .header-badge {{
    font-family: 'Fira Code', monospace;
    font-size: 0.7rem; font-weight: 600;
    color: var(--accent);
    background: var(--accent-dim);
    border: 1px solid rgba(255,108,0,0.3);
    padding: 5px 14px; border-radius: 20px;
    letter-spacing: 0.8px; text-transform: uppercase; white-space: nowrap;
  }}
  .refresh-btn {{
    font-family: 'Fira Sans', sans-serif;
    font-size: 0.8rem; font-weight: 500;
    color: var(--text-sub);
    background: var(--surface);
    border: 1px solid var(--border2);
    padding: 6px 14px; border-radius: var(--radius-sm);
    cursor: pointer; transition: all var(--transition);
    display: flex; align-items: center; gap: 6px;
    text-decoration: none;
  }}
  .refresh-btn:hover {{ border-color: var(--primary); color: var(--primary); background: rgba(59,130,246,0.08); }}
  .theme-toggle {{
    width: 36px; height: 36px; border-radius: var(--radius-sm);
    background: var(--surface2); border: 1px solid var(--border2);
    color: var(--text-muted); cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: all var(--transition); flex-shrink: 0;
  }}
  .theme-toggle:hover {{ border-color: var(--accent); color: var(--accent); background: var(--accent-dim); }}
  .theme-toggle svg {{ width: 16px; height: 16px; }}
  [data-theme="light"] .icon-moon {{ display: none; }}
  [data-theme="dark"]  .icon-sun  {{ display: none; }}

  /* ── Sticky header group (header + tabs + filters colam juntos) ── */
  .sticky-header-group {{
    position: sticky; top: 0; z-index: 300;
  }}

  /* ── Tab navigation ── */
  .tab-nav {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(8px);
  }}
  .tab-nav-inner {{
    max-width: 1280px; margin: 0 auto;
    padding: 0 32px;
    display: flex; align-items: flex-end; gap: 0;
  }}
  .tab-btn {{
    font-family: 'Fira Sans', sans-serif;
    font-size: 0.875rem; font-weight: 500;
    padding: 14px 20px;
    background: transparent; color: var(--text-muted);
    border: none; border-bottom: 2px solid transparent;
    cursor: pointer; letter-spacing: 0.2px;
    transition: all var(--transition);
    display: flex; align-items: center; gap: 8px;
  }}
  .tab-btn svg {{ width: 16px; height: 16px; flex-shrink: 0; }}
  .tab-btn:hover {{ color: var(--text-sub); }}
  .tab-btn.active {{ color: var(--accent); border-bottom-color: var(--accent); }}

  /* ── Sticky filter bar ── */
  .filter-sticky {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 10px 0;
    backdrop-filter: blur(8px);
  }}
  .filter-inner {{
    max-width: 1280px; margin: 0 auto;
    padding: 0 32px;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  }}
  .filter-label {{
    font-family: 'Fira Code', monospace;
    font-size: 0.72rem; font-weight: 500;
    color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px;
    margin-right: 4px;
  }}
  .filter-period-btn {{
    font-family: 'Fira Sans', sans-serif;
    font-size: 0.82rem; font-weight: 500;
    padding: 5px 14px; border-radius: 20px;
    border: 1px solid var(--border2);
    background: transparent; color: var(--text-muted);
    cursor: pointer; transition: all var(--transition); letter-spacing: 0.2px;
  }}
  .filter-period-btn:hover {{ border-color: var(--primary); color: var(--primary); }}
  .filter-period-btn.active {{ background: var(--primary); border-color: var(--primary); color: #FFFFFF; }}

  /* ── Layout ── */
  .container {{ max-width: 1280px; margin: 0 auto; padding: 20px 24px 40px; }}

  /* ── Section titles ── */
  .section-title {{
    font-family: 'Fira Code', monospace;
    font-size: 0.72rem; font-weight: 600;
    color: var(--text-muted); text-transform: uppercase; letter-spacing: 1.2px;
    margin-bottom: 10px;
    display: flex; align-items: center; gap: 10px;
  }}
  .section-title::before {{
    content: ''; display: inline-block;
    width: 3px; height: 14px;
    background: var(--accent); border-radius: 2px;
    box-shadow: 0 0 6px rgba(255,108,0,0.5);
  }}

  /* ── KPI cards ── */
  .cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; margin-bottom: 20px;
  }}
  .card {{
    background: var(--surface);
    border-radius: var(--radius);
    padding: 14px 16px;
    border: 1px solid var(--border);
    cursor: default;
    transition: transform var(--transition), border-color var(--transition), box-shadow var(--transition);
    position: relative; overflow: hidden;
  }}
  .card::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--primary), transparent);
    opacity: 0;
    transition: opacity var(--transition);
  }}
  .card:hover {{
    transform: translateY(-3px);
    border-color: var(--border2);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }}
  .card:hover::before {{ opacity: 1; }}
  .card .value {{
    font-family: 'Fira Code', monospace;
    font-size: 1.6rem; font-weight: 700;
    color: var(--accent); line-height: 1;
    text-shadow: 0 0 20px rgba(255,108,0,0.2);
  }}
  .card .label {{
    font-size: 0.7rem; color: var(--text-muted);
    margin-top: 6px; text-transform: uppercase;
    letter-spacing: 0.5px; line-height: 1.4;
  }}

  /* ── Chart grids ── */
  .charts-2 {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 14px; margin-bottom: 20px;
  }}
  .charts-2x2 {{
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 14px; margin-bottom: 20px;
  }}
  @media (max-width: 768px) {{
    .charts-2x2 {{ grid-template-columns: 1fr; }}
    .charts-2   {{ grid-template-columns: 1fr; }}
    .container  {{ padding: 20px 16px 48px; }}
    .header-inner {{ padding: 18px 16px; }}
    .tab-nav-inner {{ padding: 0 16px; }}
    .filter-inner {{ padding: 0 16px; }}
    .header-text h1 {{ font-size: 1.3rem; }}
  }}
  .chart-full {{ margin-bottom: 20px; }}
  .chart-box {{
    background: var(--surface);
    border-radius: var(--radius);
    padding: 16px 18px; border: 1px solid var(--border);
    display: flex; flex-direction: column;
    transition: border-color var(--transition);
  }}
  .chart-box:hover {{ border-color: var(--border2); }}
  .chart-box h3 {{
    font-family: 'Fira Code', monospace;
    font-size: 0.72rem; font-weight: 600;
    color: var(--text-sub); text-transform: uppercase; letter-spacing: 0.8px;
    margin-bottom: 12px; flex-shrink: 0;
  }}
  .chart-box canvas {{ height: 180px !important; width: 100% !important; }}

  /* ── Posts table ── */
  .table-wrapper {{
    border-radius: var(--radius); overflow: hidden;
    border: 1px solid var(--border); margin-bottom: 40px;
  }}
  table {{ width: 100%; border-collapse: collapse; background: var(--surface); }}
  th {{
    background: var(--bg); padding: 12px 12px; text-align: left;
    font-family: 'Fira Code', monospace;
    font-size: 0.7rem; font-weight: 600;
    color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px;
    border-bottom: 1px solid var(--border);
  }}
  td {{
    padding: 10px 12px; border-top: 1px solid var(--border);
    font-size: 0.84rem; vertical-align: middle; color: var(--text-sub);
  }}
  tr:hover td {{ background: rgba(30,41,59,0.5); }}
  .post-thumb {{
    width: 52px; height: 52px; object-fit: cover;
    border-radius: var(--radius-sm); display: block;
    border: 1px solid var(--border2);
    transition: border-color var(--transition);
  }}
  tr:hover .post-thumb {{ border-color: var(--primary); }}
  .caption-cell {{ max-width: 200px; color: var(--text-sub); font-size: 0.82rem; line-height: 1.4; }}

  /* ── Badges ── */
  .badge {{
    font-family: 'Fira Code', monospace;
    padding: 3px 9px; border-radius: 20px;
    font-size: 0.68rem; font-weight: 600;
    letter-spacing: 0.5px; text-transform: uppercase;
  }}
  .badge-image          {{ background: rgba(59,130,246,0.12); color: #60A5FA; border: 1px solid rgba(59,130,246,0.25); }}
  .badge-video          {{ background: rgba(239,68,68,0.12);  color: #F87171; border: 1px solid rgba(239,68,68,0.25); }}
  .badge-carousel_album {{ background: rgba(16,185,129,0.12); color: #34D399; border: 1px solid rgba(16,185,129,0.25); }}
  .badge-reel           {{ background: rgba(139,92,246,0.12); color: #A78BFA; border: 1px solid rgba(139,92,246,0.25); }}

  /* ── Analysis tab ── */
  .insight-cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px; margin-bottom: 20px;
  }}
  .insight-card {{
    background: var(--surface);
    border-radius: var(--radius);
    padding: 22px 20px; border: 1px solid var(--border); text-align: center;
    transition: border-color var(--transition), transform var(--transition);
  }}
  .insight-card:hover {{ border-color: var(--border2); transform: translateY(-2px); }}
  .insight-card .ic-value {{
    font-family: 'Fira Code', monospace;
    font-size: 1.8rem; font-weight: 700;
    color: var(--accent); line-height: 1;
    text-shadow: 0 0 16px rgba(255,108,0,0.2);
  }}
  .insight-card .ic-label {{
    font-size: 0.72rem; color: var(--text-muted);
    margin-top: 8px; text-transform: uppercase; letter-spacing: 0.5px;
  }}
  .insight-card .ic-sub {{
    font-size: 0.78rem; color: var(--text-sub); margin-top: 4px; line-height: 1.4;
  }}

  .rec-box {{
    background: var(--surface);
    border-radius: var(--radius);
    padding: 24px 28px; border: 1px solid var(--border); margin-bottom: 40px;
  }}
  .rec-box h3 {{
    font-family: 'Fira Code', monospace;
    font-size: 0.78rem; font-weight: 600;
    color: var(--accent); text-transform: uppercase; letter-spacing: 0.8px;
    margin-bottom: 18px;
  }}
  .rec-list {{ list-style: none; display: flex; flex-direction: column; gap: 10px; }}
  .rec-item {{
    background: rgba(30,41,59,0.4);
    border-left: 3px solid var(--primary);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 12px 16px;
    font-size: 0.875rem; color: var(--text-sub); line-height: 1.6;
  }}
  .rec-item strong {{ color: var(--accent); }}

  .highlight-posts {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 12px; margin-bottom: 20px;
  }}
  .post-highlight {{
    background: var(--surface);
    border-radius: var(--radius);
    padding: 16px; border: 1px solid var(--border);
    display: flex; gap: 14px; align-items: flex-start;
    transition: border-color var(--transition), transform var(--transition);
    cursor: default;
  }}
  .post-highlight:hover {{ border-color: var(--border2); transform: translateY(-2px); }}
  .ph-label {{
    font-family: 'Fira Code', monospace;
    font-size: 0.65rem; font-weight: 700; color: var(--accent);
    text-transform: uppercase; letter-spacing: 0.8px;
    white-space: nowrap; writing-mode: vertical-rl;
    text-orientation: mixed; transform: rotate(180deg);
    align-self: center;
  }}
  .ph-img {{
    width: 72px; height: 72px; object-fit: cover;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border2); flex-shrink: 0;
    transition: border-color var(--transition);
  }}
  .post-highlight:hover .ph-img {{ border-color: var(--primary); }}
  .ph-meta {{ flex: 1; min-width: 0; }}
  .ph-caption {{ font-size: 0.82rem; color: var(--text-sub); margin-bottom: 8px; line-height: 1.4; }}
  .ph-stats {{
    display: flex; flex-wrap: wrap; gap: 10px;
    font-size: 0.76rem; color: var(--text-muted);
  }}
  .ph-stat {{
    display: flex; align-items: center; gap: 4px;
  }}
  .ph-stat svg {{ width: 12px; height: 12px; flex-shrink: 0; }}
  .ph-date {{ color: var(--text-muted); }}

  .data-table-wrapper {{
    border-radius: var(--radius); overflow: hidden;
    border: 1px solid var(--border); margin-bottom: 40px;
  }}
  .data-table-wrapper table {{ background: var(--surface); }}

  /* ── Content Ideas grid ── */
  .ideas-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 16px; margin-bottom: 40px;
  }}
  .idea-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px;
    transition: all var(--transition); cursor: default;
  }}
  .idea-card:hover {{ border-color: var(--primary); background: rgba(59,130,246,0.04); }}
  .idea-format {{
    display: inline-flex; align-items: center; gap: 6px;
    font-family: 'Fira Code', monospace; font-size: 0.68rem; font-weight: 700;
    padding: 3px 10px; border-radius: 20px; margin-bottom: 12px;
    text-transform: uppercase; letter-spacing: 0.6px;
  }}
  .idea-format.reel       {{ background: rgba(139,92,246,0.15); color: #A78BFA; border: 1px solid rgba(139,92,246,0.3); }}
  .idea-format.carrossel  {{ background: rgba(16,185,129,0.15); color: #34D399; border: 1px solid rgba(16,185,129,0.3); }}
  .idea-format.foto       {{ background: rgba(59,130,246,0.15); color: #60A5FA; border: 1px solid rgba(59,130,246,0.3); }}
  .idea-format.stories    {{ background: rgba(255,108,0,0.15); color: #FF6C00; border: 1px solid rgba(255,108,0,0.3); }}
  .idea-category {{
    font-size: 0.65rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.8px; color: var(--text-muted); margin-bottom: 10px;
    display: flex; align-items: center; gap: 5px;
  }}
  .idea-category::before {{
    content: ''; width: 6px; height: 6px; border-radius: 50%;
    background: currentColor; display: inline-block;
  }}
  .idea-category.eletrica    {{ color: #FF6C00; }}
  .idea-category.climatizacao {{ color: #38BDF8; }}
  .idea-category.tecnologia  {{ color: #A78BFA; }}
  .idea-category.cursos      {{ color: #34D399; }}
  .idea-title {{
    font-size: 0.9rem; font-weight: 600; color: var(--text);
    margin-bottom: 8px; line-height: 1.4;
  }}
  .idea-why {{ font-size: 0.8rem; color: var(--text-muted); line-height: 1.5; }}
  .idea-potential {{
    margin-top: 12px; font-size: 0.75rem; color: var(--accent);
    font-family: 'Fira Code', monospace; font-weight: 600;
  }}
  .idea-done-btn {{
    margin-top: 14px; width: 100%;
    font-family: 'Fira Sans', sans-serif; font-size: 0.78rem; font-weight: 500;
    color: var(--text-muted); background: transparent;
    border: 1px solid var(--border2); border-radius: var(--radius-sm);
    padding: 7px 12px; cursor: pointer; transition: all var(--transition);
    display: flex; align-items: center; justify-content: center; gap: 6px;
  }}
  .idea-done-btn:hover {{ border-color: var(--green); color: var(--green); background: rgba(16,185,129,0.06); }}
  .idea-done-btn--undo:hover {{ border-color: var(--text-muted); color: var(--text-muted); background: transparent; }}
  .idea-covered-badge {{
    font-size: 0.68rem; font-family: 'Fira Code', monospace; font-weight: 600;
    color: var(--accent); border: 1px solid rgba(255,108,0,0.3);
    background: rgba(255,108,0,0.08); padding: 2px 8px; border-radius: 10px;
    display: inline-block; margin-bottom: 8px; letter-spacing: 0.3px;
  }}
  .idea-section-divider {{
    grid-column: 1 / -1; display: flex; align-items: center; gap: 12px;
    margin: 8px 0 4px; color: var(--text-muted); font-size: 0.78rem;
  }}
  .idea-section-divider::before, .idea-section-divider::after {{
    content: ''; flex: 1; height: 1px; background: var(--border);
  }}
  .idea-ref-post {{
    margin-top: 12px; padding: 10px; border-radius: var(--radius-sm);
    background: var(--bg); border: 1px solid var(--border);
    display: flex; align-items: flex-start; gap: 10px; text-decoration: none;
    transition: border-color var(--transition);
  }}
  .idea-ref-post:hover {{ border-color: var(--border2); }}
  .idea-ref-img {{
    width: 44px; height: 44px; border-radius: 6px; object-fit: cover;
    flex-shrink: 0; background: var(--surface2);
  }}
  .idea-ref-text {{ flex: 1; min-width: 0; }}
  .idea-ref-label {{
    font-size: 0.68rem; font-family: 'Fira Code', monospace;
    color: var(--text-muted); margin-bottom: 3px;
  }}
  .idea-ref-caption {{
    font-size: 0.78rem; color: var(--text-sub); line-height: 1.4;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}
  .idea-ref-date {{ font-size: 0.68rem; color: var(--text-muted); margin-top: 3px; }}

  /* ── Hashtags por área ── */
  .hashtag-areas {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 16px; margin-bottom: 40px;
  }}
  .hashtag-area-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px;
  }}
  .hashtag-area-title {{
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.8px; margin-bottom: 14px;
    display: flex; align-items: center; gap: 6px;
  }}
  .hashtag-area-title::before {{
    content: ''; width: 8px; height: 8px; border-radius: 50%; background: currentColor;
  }}
  .hashtag-area-title.eletrica    {{ color: #FF6C00; }}
  .hashtag-area-title.climatizacao {{ color: #38BDF8; }}
  .hashtag-area-title.tecnologia  {{ color: #A78BFA; }}
  .hashtag-area-title.cursos      {{ color: #34D399; }}
  .hashtag-chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .hashtag-chip {{
    font-family: 'Fira Code', monospace; font-size: 0.72rem;
    background: var(--bg); border: 1px solid var(--border2);
    border-radius: 6px; padding: 4px 10px; color: var(--text-sub);
    cursor: pointer; transition: all var(--transition); user-select: all;
  }}
  .hashtag-chip:hover {{ border-color: var(--accent); color: var(--accent); background: rgba(255,108,0,0.06); }}
  .hashtag-copy-btn {{
    margin-top: 14px; width: 100%;
    font-family: 'Fira Sans', sans-serif; font-size: 0.75rem; font-weight: 500;
    color: var(--text-muted); background: transparent;
    border: 1px solid var(--border2); border-radius: var(--radius-sm);
    padding: 6px 12px; cursor: pointer; transition: all var(--transition);
    display: flex; align-items: center; justify-content: center; gap: 6px;
  }}
  .hashtag-copy-btn:hover {{ border-color: var(--primary); color: var(--primary); background: rgba(59,130,246,0.06); }}
  @media (max-width: 640px) {{
    .ideas-grid  {{ grid-template-columns: 1fr; }}
    .hashtag-areas {{ grid-template-columns: 1fr; }}
  }}

  /* ── Footer ── */
  .updated {{
    text-align: right; font-size: 0.7rem; color: var(--text-muted);
    margin-top: 8px;
    font-family: 'Fira Code', monospace; letter-spacing: 0.3px;
  }}

  /* ── Tab content ── */
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}

  /* ── Scrollbar ── */
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: var(--bg); }}
  ::-webkit-scrollbar-thumb {{ background: var(--border2); border-radius: 3px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: var(--text-muted); }}
</style>
</head>
<body>

<!-- ═══════════════════════ STICKY GROUP ═══════════════════════ -->
<div class="sticky-header-group">

<!-- ═══════════════════════ HEADER ═══════════════════════ -->
<header>
  <div class="header-inner">
    <div class="header-accent"></div>
    <img src="{perfil.get('profile_picture_url', '')}" onerror="this.style.display='none'" alt="Foto de perfil @{perfil.get('username', '')}">
    <div class="header-text">
      <h1><span>@</span>{perfil.get('username', 'engehalleletrica')}</h1>
      <p>{perfil.get('biography', '')}</p>
    </div>
    <div class="header-right">
      <div class="header-badge">Analytics</div>
      <button class="theme-toggle" onclick="toggleTheme()" title="Alternar tema" aria-label="Alternar tema claro/escuro">
        <svg class="icon-moon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
        <svg class="icon-sun" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
      </button>
      <a href="/refresh" class="refresh-btn" title="Atualizar dados">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
        Atualizar
      </a>
    </div>
  </div>
</header>

<!-- ═══════════════════════ TAB NAVIGATION ═══════════════════════ -->
<div class="tab-nav">
  <div class="tab-nav-inner">
    <button class="tab-btn active" onclick="showTab('tab-dashboard', this)">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
      Dashboard
    </button>
    <button class="tab-btn" onclick="showTab('tab-analise', this)">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
      Análise
    </button>
  </div>
</div>

<!-- ═══════════════════════ STICKY FILTER BAR ═══════════════════════ -->
<div class="filter-sticky">
  <div class="filter-inner">
    <span class="filter-label">Período</span>
    <button class="filter-period-btn" data-days="7">7 dias</button>
    <button class="filter-period-btn" data-days="15">15 dias</button>
    <button class="filter-period-btn active" data-days="30">30 dias</button>
    <button class="filter-period-btn" data-days="90">3 meses</button>
    <button class="filter-period-btn" data-days="0">Tudo</button>
  </div>
</div>

</div><!-- /sticky-header-group -->

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: DASHBOARD                                                  -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-dashboard" class="tab-content active">
<div class="container">

  <div class="section-title">Resumo da conta</div>
  <div class="cards">
    <div class="card">
      <div class="value">{perfil.get('followers_count', 0):,}</div>
      <div class="label">Seguidores</div>
    </div>
    <div class="card">
      <div class="value">{perfil.get('follows_count', 0):,}</div>
      <div class="label">Seguindo</div>
    </div>
    <div class="card">
      <div class="value">{perfil.get('media_count', 0):,}</div>
      <div class="label">Publicações</div>
    </div>
    <div class="card">
      <div class="value">{total_curtidas:,}</div>
      <div class="label">Curtidas (últimos {total_posts} posts)</div>
    </div>
    <div class="card">
      <div class="value">{total_comentarios:,}</div>
      <div class="label">Comentários (últimos {total_posts} posts)</div>
    </div>
    <div class="card">
      <div class="value">{engajamento_medio}</div>
      <div class="label">Engajamento médio por post</div>
    </div>
  </div>

  <div class="section-title">Métricas da conta</div>
  <div class="charts-2">
    <div class="chart-box">
      <h3>Alcance diário</h3>
      <canvas id="chartAlcance"></canvas>
    </div>
    <div class="chart-box">
      <h3>Crescimento de seguidores</h3>
      <canvas id="chartSeguidores"></canvas>
    </div>
  </div>

  <div class="section-title">Análise de posts</div>
  <div class="charts-2x2">
    <div class="chart-box">
      <h3>Curtidas e comentários por data</h3>
      <canvas id="chartTimeline"></canvas>
    </div>
    <div class="chart-box">
      <h3>Engajamento médio por tipo de post</h3>
      <canvas id="chartTipos"></canvas>
    </div>
    <div class="chart-box">
      <h3>Distribuição de tipos de conteúdo</h3>
      <canvas id="chartDonut"></canvas>
    </div>
    <div class="chart-box">
      <h3>Top 5 posts por curtidas
        <small style="color:var(--text-muted);font-size:0.65rem;font-family:'Fira Sans',sans-serif;font-weight:400;text-transform:none;letter-spacing:0"> — clique para abrir</small>
      </h3>
      <canvas id="chartTop5" style="cursor:pointer"></canvas>
    </div>
  </div>

  <div class="section-title">Compartilhamentos e salvos</div>
  <div class="chart-full">
    <div class="chart-box">
      <h3>Shares e salvos por post (últimos 10 posts do período)</h3>
      <canvas id="chartSharesSavos"></canvas>
    </div>
  </div>

  <div class="section-title">Últimas publicações</div>
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th>Imagem</th><th>Legenda</th><th>Tipo</th><th>Data</th>
          <th>Curtidas</th><th>Comentários</th><th>Alcance</th>
          <th>Interações</th><th>Salvos</th><th>Views</th>
        </tr>
      </thead>
      <tbody>{posts_html}</tbody>
    </table>
  </div>
  <p class="updated">Atualizado em: {coletado_em}</p>
</div>
</div>

<!-- ═══════════════════════════════════════════════════════════════ -->
<!-- TAB: ANÁLISE & RECOMENDAÇÕES                                    -->
<!-- ═══════════════════════════════════════════════════════════════ -->
<div id="tab-analise" class="tab-content">
<div class="container">

  <div class="section-title">Indicadores-chave</div>
  <div class="insight-cards">
    <div class="insight-card">
      <div class="ic-value" id="ic-eng-rate">—</div>
      <div class="ic-label">Taxa de engajamento</div>
      <div class="ic-sub" id="ic-eng-rate-sub">(curtidas + comentários) / seguidores</div>
    </div>
    <div class="insight-card">
      <div class="ic-value" id="ic-melhor-tipo">—</div>
      <div class="ic-label">Melhor tipo de conteúdo</div>
      <div class="ic-sub" id="ic-melhor-tipo-sub">—</div>
    </div>
    <div class="insight-card">
      <div class="ic-value" id="ic-melhor-dia">—</div>
      <div class="ic-label">Melhor dia para postar</div>
      <div class="ic-sub" id="ic-melhor-dia-sub">—</div>
    </div>
    <div class="insight-card">
      <div class="ic-value" id="ic-melhor-hora">—</div>
      <div class="ic-label">Horário mais usado</div>
      <div class="ic-sub" id="ic-melhor-hora-sub">—</div>
    </div>
    <div class="insight-card">
      <div class="ic-value" id="ic-freq">—</div>
      <div class="ic-label">Posts por semana</div>
      <div class="ic-sub" id="ic-freq-sub">Frequência média no período</div>
    </div>
  </div>

  <div class="section-title">Ideias de Conteúdo para Esta Semana</div>
  <div class="ideas-grid" id="ideas-grid"></div>

  <div class="section-title">Posts em destaque</div>
  <div class="highlight-posts" id="highlight-posts-container"></div>

  <div class="section-title">Recomendações estratégicas</div>
  <div class="rec-box">
    <h3>Insights</h3>
    <ul class="rec-list" id="rec-list"></ul>
  </div>

  <div class="section-title">Hashtags por Área</div>
  <div class="hashtag-areas" id="hashtag-areas"></div>

  <div class="section-title">Desempenho por tipo de conteúdo</div>
  <div class="data-table-wrapper">
    <table>
      <thead>
        <tr>
          <th>Tipo</th><th>Posts</th><th>Média Curtidas</th>
          <th>Média Comentários</th><th>Média Shares</th>
          <th>Média Salvos</th><th>Média Alcance</th>
        </tr>
      </thead>
      <tbody id="tipo-table-body"></tbody>
    </table>
  </div>

  <div class="section-title">Engajamento por dia da semana</div>
  <div class="data-table-wrapper">
    <table>
      <thead>
        <tr>
          <th>Dia</th><th>Posts publicados</th>
          <th>Média Curtidas</th><th>Média Comentários</th>
        </tr>
      </thead>
      <tbody id="dow-table-body"></tbody>
    </table>
  </div>

  <p class="updated" id="analise-footer">Análise baseada em {total_posts} posts · Atualizado em: {coletado_em}</p>
</div>
</div>

<!-- ═══════════════════════ SCRIPTS ═══════════════════════ -->
<script>
// ── Constants ────────────────────────────────────────────────────────────────
const FOLLOWERS_COUNT  = {followers_count};
const COLETADO_EM      = '{coletado_em}';
const HASHTAGS_POR_AREA = {hashtags_json};
const DOW_PT = ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo'];

// ── Tab switching ─────────────────────────────────────────────────────────────
function showTab(tabId, btn) {{
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  btn.classList.add('active');
  if (tabId === 'tab-analise') {{ updateAnalysis(currentFilteredPosts); renderHashtagAreas(); }}
}}

// ── Brand colours ─────────────────────────────────────────────────────────────
const C_AMBER  = '#FF6C00';
const C_BLUE   = '#3B82F6';
const C_VIOLET = '#8B5CF6';
const C_GREEN  = '#10B981';
const C_RED    = '#EF4444';

// ── Theme helpers ─────────────────────────────────────────────────────────────
function isLight() {{ return document.documentElement.getAttribute('data-theme') === 'light'; }}
function themeGrid()   {{ return isLight() ? 'rgba(203,213,225,0.6)' : 'rgba(30,41,59,0.6)'; }}
function themeTick()   {{ return isLight() ? '#94A3B8' : '#334155'; }}
function themeLegend() {{ return isLight() ? '#475569' : '#94A3B8'; }}

// ── Chart defaults ────────────────────────────────────────────────────────────
function makeScales() {{
  const g = themeGrid(), t = themeTick();
  return {{
    x: {{ ticks: {{ color: t, maxTicksLimit: 8, font: {{ family: 'Fira Sans', size: 11 }} }}, grid: {{ color: g }} }},
    y: {{ ticks: {{ color: t, font: {{ family: 'Fira Sans', size: 11 }} }},                   grid: {{ color: g }} }}
  }};
}}
function makeLegend() {{
  return {{ display: true, labels: {{ color: themeLegend(), font: {{ family: 'Fira Sans', size: 12 }}, padding: 16 }} }};
}}
const baseScales = makeScales();
const baseLegend = makeLegend();
const allCharts  = [];

// ── Theme toggle ──────────────────────────────────────────────────────────────
function applyChartTheme() {{
  const g = themeGrid(), t = themeTick(), l = themeLegend();
  // Atualiza borderColor do donut (separa as fatias)
  if (donutChart?.data?.datasets?.[0]) {{
    donutChart.data.datasets[0].borderColor = isLight() ? 'rgba(248,250,252,0.6)' : 'rgba(2,8,23,0.3)';
  }}
  allCharts.forEach(chart => {{
    if (chart.options.scales) {{
      Object.values(chart.options.scales).forEach(scale => {{
        if (scale.grid)  scale.grid.color  = g;
        if (scale.ticks) scale.ticks.color = t;
      }});
    }}
    if (chart.options.plugins?.legend?.labels) {{
      chart.options.plugins.legend.labels.color = l;
    }}
    chart.update('none');
  }});
}}

function toggleTheme() {{
  const next = isLight() ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('engehall_theme', next);
  applyChartTheme();
}}

// ── Embedded data ─────────────────────────────────────────────────────────────
const allPostsData     = {posts_json};
const allReachData     = {reach_series_json};
const allFollowersData = {followers_series_json};

// ── Date filter ───────────────────────────────────────────────────────────────
function getDateCutoff(days) {{
  if (days === 0) return null;
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}}
function filterByDays(arr, days, dateField) {{
  const cutoff = getDateCutoff(days);
  if (!cutoff) return arr;
  return arr.filter(item => item[dateField] >= cutoff);
}}

// ── Chart instances ───────────────────────────────────────────────────────────

const alcanceChart = new Chart(document.getElementById('chartAlcance'), {{
  type: 'line',
  data: {{
    labels: [],
    datasets: [{{
      label: 'Alcance',
      data: [],
      borderColor: C_BLUE,
      backgroundColor: 'rgba(59,130,246,0.08)',
      fill: true, tension: 0.4,
      pointRadius: 3, pointHoverRadius: 6,
      pointBackgroundColor: C_BLUE,
    }}]
  }},
  options: {{
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{ legend: {{ display: false }} }},
    scales: baseScales
  }}
}});

const seguidoresChart = new Chart(document.getElementById('chartSeguidores'), {{
  type: 'bar',
  data: {{
    labels: [],
    datasets: [{{
      label: 'Seguidores',
      data: [],
      backgroundColor: 'rgba(59,130,246,0.6)',
      borderColor: C_BLUE,
      borderWidth: 1, borderRadius: 4
    }}]
  }},
  options: {{
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{ legend: {{ display: false }} }},
    scales: baseScales
  }}
}});

const timelineChart = new Chart(document.getElementById('chartTimeline'), {{
  type: 'line',
  data: {{
    labels: {timeline_labels},
    datasets: [
      {{
        label: 'Curtidas', data: {timeline_curtidas},
        borderColor: C_AMBER, backgroundColor: 'rgba(255,108,0,0.08)',
        fill: true, tension: 0.4, pointRadius: 3, pointBackgroundColor: C_AMBER
      }},
      {{
        label: 'Comentários', data: {timeline_comentarios},
        borderColor: C_VIOLET, backgroundColor: 'rgba(139,92,246,0.08)',
        fill: true, tension: 0.4, pointRadius: 3, pointBackgroundColor: C_VIOLET
      }}
    ]
  }},
  options: {{
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{ legend: baseLegend }},
    scales: baseScales
  }}
}});

const tiposChart = new Chart(document.getElementById('chartTipos'), {{
  type: 'bar',
  data: {{
    labels: {tipos_labels_json},
    datasets: [
      {{ label: 'Média de Curtidas',    data: {tipos_curtidas_json},    backgroundColor: 'rgba(255,108,0,0.75)', borderRadius: 4 }},
      {{ label: 'Média de Comentários', data: {tipos_comentarios_json}, backgroundColor: 'rgba(139,92,246,0.75)', borderRadius: 4 }}
    ]
  }},
  options: {{
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{ legend: baseLegend }},
    scales: baseScales
  }}
}});

const donutChart = new Chart(document.getElementById('chartDonut'), {{
  type: 'doughnut',
  data: {{
    labels: {donut_labels},
    datasets: [{{
      data: {donut_data},
      backgroundColor: [C_VIOLET, C_RED, C_AMBER, C_GREEN],
      borderColor: isLight() ? 'rgba(248,250,252,0.6)' : 'rgba(2,8,23,0.3)', borderWidth: 2,
      hoverOffset: 6
    }}]
  }},
  options: {{
    maintainAspectRatio: false,
    plugins: {{
      legend: {{
        display: true, position: 'bottom',
        labels: {{ color: '#94A3B8', font: {{ family: 'Fira Sans', size: 12 }}, padding: 20 }}
      }}
    }}
  }}
}});

const top5Chart = new Chart(document.getElementById('chartTop5'), {{
  type: 'bar',
  data: {{
    labels: {top5_labels},
    datasets: [{{
      label: 'Curtidas', data: {top5_curtidas},
      backgroundColor: 'rgba(255,108,0,0.75)',
      borderColor: C_AMBER, borderWidth: 1, borderRadius: 4
    }}]
  }},
  options: {{
    indexAxis: 'y',
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{ callbacks: {{ title: (items) => items[0].label }} }}
    }},
    scales: {{
      x: {{ ticks: {{ color: themeTick() }}, grid: {{ color: themeGrid() }} }},
      y: {{ ticks: {{ color: themeTick(), font: {{ size: 11, family: 'Fira Sans' }} }}, grid: {{ color: themeGrid() }} }}
    }},
    onClick: (evt, elements) => {{
      if (elements.length > 0) {{
        const url = top5Chart._permalinks?.[elements[0].index];
        if (url && url !== '#') window.open(url, '_blank');
      }}
    }}
  }}
}});
top5Chart._permalinks = {top5_links};

document.getElementById('chartTop5').addEventListener('mousemove', function(e) {{
  const pts = top5Chart.getElementsAtEventForMode(e, 'nearest', {{ intersect: true }}, false);
  this.style.cursor = pts.length ? 'pointer' : 'default';
}});

const sharesSavosChart = new Chart(document.getElementById('chartSharesSavos'), {{
  type: 'bar',
  data: {{
    labels: {shares_salvos_labels},
    datasets: [
      {{ label: 'Compartilhamentos', data: {shares_salvos_shares}, backgroundColor: 'rgba(255,108,0,0.75)', borderRadius: 4 }},
      {{ label: 'Salvos',            data: {shares_salvos_saved},  backgroundColor: 'rgba(59,130,246,0.6)',  borderRadius: 4 }}
    ]
  }},
  options: {{
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{ legend: baseLegend }},
    scales: baseScales
  }}
}});

// Registrar todos os charts para atualização de tema
allCharts.push(alcanceChart, seguidoresChart, timelineChart, tiposChart, donutChart, top5Chart, sharesSavosChart);

// ── Analysis helpers ──────────────────────────────────────────────────────────
function jAvg(arr) {{
  return arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length * 10) / 10 : 0;
}}

const SVG_HEART    = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>`;
const SVG_EYE      = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`;
const SVG_BOOKMARK = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>`;

function postCard(p, label) {{
  if (!p) return '';
  const cap  = (p.caption || 'sem legenda').slice(0, 50);
  const link = p.permalink || '#';
  const img  = p.img || '';
  return `
  <div class="post-highlight">
    <div class="ph-label">${{label}}</div>
    <a href="${{link}}" target="_blank" rel="noopener">
      <img src="${{img}}" class="ph-img" alt="Post" loading="lazy" onerror="this.src='https://placehold.co/80x80/0F172A/FF6C00?text=?'">
    </a>
    <div class="ph-meta">
      <div class="ph-caption">${{cap}}</div>
      <div class="ph-stats">
        <span class="ph-stat">${{SVG_HEART}} ${{p.like_count}}</span>
        <span class="ph-stat">${{SVG_EYE}} ${{p.reach || '—'}}</span>
        <span class="ph-stat">${{SVG_BOOKMARK}} ${{p.saved || '—'}}</span>
        <span class="ph-date">${{p.timestamp}}</span>
      </div>
    </div>
  </div>`;
}}

// ── Content ideas generator ───────────────────────────────────────────────────
function generateContentIdeas(posts) {{
  // Últimos 15 posts ordenados por data para detectar temas já cobertos
  const recentPosts = [...posts]
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    .slice(0, 15);

  // Retorna o post que gerou a detecção, ou null
  function findMatchingPost(keywords) {{
    for (const kw of keywords) {{
      const found = recentPosts.find(p => (p.caption || '').toLowerCase().includes(kw));
      if (found) return {{ post: found, keyword: kw }};
    }}
    return null;
  }}

  const doneIds = new Set(JSON.parse(localStorage.getItem('ideas_done') || '[]'));

  const avg = arr => arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : 0;
  const tiposMap = {{}};
  posts.forEach(p => {{
    if (!tiposMap[p.media_type]) tiposMap[p.media_type] = {{ likes: [], count: 0 }};
    tiposMap[p.media_type].likes.push(p.like_count);
    tiposMap[p.media_type].count++;
  }});
  const reelAvg  = avg((tiposMap['REEL'] || {{}}).likes || []);
  const imgAvg   = avg((tiposMap['IMAGE'] || {{}}).likes || []);
  const carCount = (tiposMap['CAROUSEL_ALBUM'] || {{}}).count || 0;
  const carAvg   = avg((tiposMap['CAROUSEL_ALBUM'] || {{}}).likes || []);

  const allIdeas = [
    // ── ELÉTRICA ──────────────────────────────────────────────────────────────
    {{
      id: 'reel-instalacao', format: 'reel', label: 'Reel', category: 'eletrica', categoryLabel: 'Elétrica',
      title: 'Instalação elétrica do início ao fim (30-60s)',
      why: 'Mostre um serviço real: painel, tomadas ou iluminação. Reels têm alcance 3× maior que fotos no algoritmo atual.',
      potential: reelAvg > imgAvg ? `Reels rendem ${{reelAvg}} curtidas na sua conta` : '↑ Alto potencial de novos seguidores',
      keywords: ['instala', 'painel', 'tomada', 'ilumina', 'fiação', 'quadro elétrico'],
    }},
    {{
      id: 'carrossel-erros', format: 'carrossel', label: 'Carrossel', category: 'eletrica', categoryLabel: 'Elétrica',
      title: '5 erros elétricos perigosos em casa',
      why: 'Conteúdo de alerta gera saves e compartilhamentos. Funciona muito bem para o nicho técnico.',
      potential: carCount < 5 ? 'Pouco explorado — grande oportunidade' : `Carrosséis rendem ${{carAvg}} curtidas na sua conta`,
      keywords: ['erro', 'perigo', 'perigoso', 'risco', 'cuidado', 'atenção'],
    }},
    {{
      id: 'reel-disjuntor', format: 'reel', label: 'Reel', category: 'eletrica', categoryLabel: 'Elétrica',
      title: 'Como identificar fio fase, neutro e terra (dica rápida)',
      why: 'Dicas técnicas de 15-30s têm ótimo desempenho. Conteúdo útil = salvo e compartilhado.',
      potential: '↑ Alcance orgânico com hashtags do nicho',
      keywords: ['fio', 'fase', 'neutro', 'terra', 'identificar', 'disjuntor', 'cor do fio'],
    }},
    // ── CLIMATIZAÇÃO ──────────────────────────────────────────────────────────
    {{
      id: 'reel-arcondicionado', format: 'reel', label: 'Reel', category: 'climatizacao', categoryLabel: 'Climatização',
      title: 'Instalação de ar condicionado inverter passo a passo',
      why: 'Conteúdo de instalação tem alto alcance. Pessoas que compraram aparelho buscam esse conteúdo ativamente.',
      potential: '↑ Alto volume de busca no Instagram',
      keywords: ['ar condicionado', 'inverter', 'split', 'climatiz', 'arcondicionado'],
    }},
    {{
      id: 'carrossel-manutencao-ar', format: 'carrossel', label: 'Carrossel', category: 'climatizacao', categoryLabel: 'Climatização',
      title: 'Quando fazer manutenção do ar condicionado? Guia completo',
      why: 'Conteúdo sazonal (verão/inverno) gera pico de engajamento. Salvo para consultar depois.',
      potential: '↑ Alta taxa de salvamento + compartilhamento',
      keywords: ['manutenção', 'limpeza', 'filtro', 'ar condicionado', 'higienizacao'],
    }},
    // ── SOLUÇÕES TECNOLÓGICAS / LED ────────────────────────────────────────────
    {{
      id: 'reel-perfil-led', format: 'reel', label: 'Reel', category: 'tecnologia', categoryLabel: 'Tecnologia',
      title: 'Antes e depois: perfil de LED em sala de estar',
      why: 'Transformações visuais com LED têm engajamento altíssimo. Pessoas marcam amigos e salvam para reforma.',
      potential: '↑ Compartilhamento máximo — pessoas marcam amigos',
      keywords: ['perfil de led', 'led', 'iluminação led', 'fita led', 'sanca'],
    }},
    {{
      id: 'carrossel-led-vantagens', format: 'carrossel', label: 'Carrossel', category: 'tecnologia', categoryLabel: 'Tecnologia',
      title: 'Por que trocar lâmpada comum por perfil de LED?',
      why: 'Comparativo de custos e economia gera saves. Ótimo para apresentar o serviço e gerar orçamentos.',
      potential: '↑ Alta conversão em pedidos de orçamento',
      keywords: ['lâmpada', 'economia', 'led', 'tecnologia', 'automação', 'smart'],
    }},
    // ── PROMOÇÃO DE CURSOS ────────────────────────────────────────────────────
    {{
      id: 'stories-curso-eletrica', format: 'stories', label: 'Stories', category: 'cursos', categoryLabel: 'Cursos',
      title: 'Enquete: você quer aprender Elétrica Predial ou Industrial?',
      why: 'Stories interativos mapeiam interesse do público e aquecem o funil para os cursos da Engehall.',
      potential: '↑ Gera leads qualificados para os cursos',
      keywords: ['curso', 'aprenda', 'elétrica predial', 'industrial', 'capacitação'],
    }},
    {{
      id: 'carrossel-curso-conteudo', format: 'carrossel', label: 'Carrossel', category: 'cursos', categoryLabel: 'Cursos',
      title: 'O que você aprende no Curso de Elétrica Predial da Engehall?',
      why: 'Carrosséis de "o que você aprende" convertem muito. Mostram valor antes de apresentar o preço.',
      potential: '↑ Alta conversão em matrículas',
      keywords: ['curso', 'aprender', 'módulo', 'certificado', 'formação', 'engehall'],
    }},
  ];

  // Enriquecer cada ideia com o post de referência detectado
  const ideasWithMatch = allIdeas.map(i => ({{
    ...i, match: findMatchingPost(i.keywords)
  }}));

  const active  = ideasWithMatch.filter(i => !doneIds.has(i.id) && !i.match);
  const covered = ideasWithMatch.filter(i => !doneIds.has(i.id) &&  i.match);
  const done    = ideasWithMatch.filter(i =>  doneIds.has(i.id));

  const SVG_CHECK = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
  const SVG_UNDO  = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/></svg>`;

  function refPostHtml(match) {{
    if (!match) return '';
    const p = match.post;
    const cap = (p.caption || 'sem legenda').slice(0, 60);
    const img = p.img || '';
    const link = p.permalink || '#';
    const date = p.timestamp || '';
    return `<a href="${{link}}" target="_blank" rel="noopener" class="idea-ref-post">
      <img src="${{img}}" class="idea-ref-img" alt="Post de referência" loading="lazy"
           onerror="this.style.display='none'">
      <div class="idea-ref-text">
        <div class="idea-ref-label">Referência detectada · "${{match.keyword}}"</div>
        <div class="idea-ref-caption">${{cap}}</div>
        <div class="idea-ref-date">${{date}}</div>
      </div>
    </a>`;
  }}

  function cardHtml(idea, state) {{
    const isPast  = state === 'covered' || state === 'done';
    const style   = isPast ? ' style="opacity:0.55"' : '';
    const isDone  = state === 'done';

    const badge = state === 'covered'
      ? `<div class="idea-covered-badge">Postado recentemente</div>`
      : isDone
        ? `<div class="idea-covered-badge" style="color:var(--green);border-color:rgba(16,185,129,0.3);background:rgba(16,185,129,0.08)">Marcado como feito</div>`
        : '';

    const ref = state === 'covered' ? refPostHtml(idea.match) : '';

    const btn = isPast
      ? `<button class="idea-done-btn idea-done-btn--undo" onclick="unmarkIdeaDone('${{idea.id}}')">${{SVG_UNDO}} Remover daqui</button>`
      : `<button class="idea-done-btn" onclick="markIdeaDone('${{idea.id}}')">${{SVG_CHECK}} Marcar como feito</button>`;

    return `<div class="idea-card"${{style}}>
      <div class="idea-category ${{idea.category}}">${{idea.categoryLabel}}</div>
      <div class="idea-format ${{idea.format}}">${{idea.label}}</div>
      ${{badge}}
      <div class="idea-title">${{idea.title}}</div>
      <div class="idea-why">${{idea.why}}</div>
      <div class="idea-potential">${{isPast ? '' : idea.potential}}</div>
      ${{ref}}
      ${{btn}}
    </div>`;
  }}

  let html = active.map(i => cardHtml(i, 'active')).join('');
  if (!active.length && !covered.length && !done.length) {{
    html = '<p class="updated" style="grid-column:1/-1">Nenhuma ideia disponível.</p>';
  }}

  // Seção única "Já postado recentemente" — auto-detectado + marcado manualmente
  const pastCards = [
    ...covered.map(i => cardHtml(i, 'covered')),
    ...done.map(i => cardHtml(i, 'done')),
  ];
  if (pastCards.length) {{
    html += `<div class="idea-section-divider"><span>Já postado recentemente</span></div>`;
    html += pastCards.join('');
  }}

  document.getElementById('ideas-grid').innerHTML = html;
}}

window.markIdeaDone = function(id) {{
  const doneIds = new Set(JSON.parse(localStorage.getItem('ideas_done') || '[]'));
  doneIds.add(id);
  localStorage.setItem('ideas_done', JSON.stringify([...doneIds]));
  generateContentIdeas(currentFilteredPosts);
}};

window.unmarkIdeaDone = function(id) {{
  const doneIds = new Set(JSON.parse(localStorage.getItem('ideas_done') || '[]'));
  doneIds.delete(id);
  localStorage.setItem('ideas_done', JSON.stringify([...doneIds]));
  generateContentIdeas(currentFilteredPosts);
}};

// ── Hashtags por área ─────────────────────────────────────────────────────────
function renderHashtagAreas() {{
  const SVG_COPY = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>`;
  const SVG_OK   = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;

  document.getElementById('hashtag-areas').innerHTML = HASHTAGS_POR_AREA.map(area => `
    <div class="hashtag-area-card">
      <div class="hashtag-area-title ${{area.cls}}">${{area.area}}</div>
      <div class="hashtag-chips">
        ${{area.tags.map(t => `<span class="hashtag-chip">${{t}}</span>`).join('')}}
      </div>
      <button class="hashtag-copy-btn" onclick="copyHashtags(this, '${{area.cls}}')" data-tags="${{area.tags.join(' ')}}">
        ${{SVG_COPY}} Copiar todos
      </button>
    </div>
  `).join('');
}}

window.copyHashtags = function(btn, cls) {{
  const tags = btn.dataset.tags;
  navigator.clipboard.writeText(tags).then(() => {{
    const original = btn.innerHTML;
    btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg> Copiado!`;
    btn.style.color = 'var(--green)';
    btn.style.borderColor = 'var(--green)';
    setTimeout(() => {{
      btn.innerHTML = original;
      btn.style.color = '';
      btn.style.borderColor = '';
    }}, 2000);
  }});
}};

// ── Analysis update ───────────────────────────────────────────────────────────
function updateAnalysis(filteredPosts) {{
  if (!filteredPosts || !filteredPosts.length) return;
  generateContentIdeas(filteredPosts);

  const totalLikes = filteredPosts.reduce((s, p) => s + p.like_count, 0);
  const totalComs  = filteredPosts.reduce((s, p) => s + p.comments_count, 0);
  const engRate    = ((totalLikes + totalComs) / filteredPosts.length / FOLLOWERS_COUNT * 100).toFixed(2);
  document.getElementById('ic-eng-rate').textContent     = engRate + '%';
  document.getElementById('ic-eng-rate-sub').textContent = '(curtidas + comentários) / seguidores';

  const tiposMap = {{}};
  filteredPosts.forEach(p => {{
    if (!tiposMap[p.media_type]) tiposMap[p.media_type] = {{ likes: [], comments: [], shares: [], saved: [], reach: [] }};
    tiposMap[p.media_type].likes.push(p.like_count);
    tiposMap[p.media_type].comments.push(p.comments_count);
    tiposMap[p.media_type].shares.push(p.shares);
    tiposMap[p.media_type].saved.push(p.saved);
    if (p.reach > 0) tiposMap[p.media_type].reach.push(p.reach);
  }});
  let bestType = '—', bestTypeAvg = -1;
  Object.entries(tiposMap).forEach(([t, s]) => {{
    const a = jAvg(s.likes);
    if (a > bestTypeAvg) {{ bestTypeAvg = a; bestType = t; }}
  }});
  document.getElementById('ic-melhor-tipo').textContent     = bestType;
  document.getElementById('ic-melhor-tipo-sub').textContent = `Média de ${{bestTypeAvg}} curtidas`;

  const dowMap = {{}};
  filteredPosts.forEach(p => {{
    if (!p.timestamp) return;
    const jsDay = new Date(p.timestamp + 'T12:00:00').getDay();
    const d     = (jsDay + 6) % 7;
    if (!dowMap[d]) dowMap[d] = {{ likes: [], comments: [], count: 0 }};
    dowMap[d].likes.push(p.like_count);
    dowMap[d].comments.push(p.comments_count);
    dowMap[d].count++;
  }});
  let bestDow = -1, bestDowAvg = -1;
  Object.entries(dowMap).forEach(([d, s]) => {{
    const a = jAvg(s.likes);
    if (a > bestDowAvg) {{ bestDowAvg = a; bestDow = parseInt(d); }}
  }});
  document.getElementById('ic-melhor-dia').textContent     = bestDow >= 0 ? DOW_PT[bestDow] : '—';
  document.getElementById('ic-melhor-dia-sub').textContent = bestDow >= 0
    ? `Média de ${{bestDowAvg}} curtidas (${{dowMap[bestDow].count}} posts)`
    : 'Dados insuficientes';

  const horaMap = {{}};
  filteredPosts.forEach(p => {{
    if (p.hour >= 0) horaMap[p.hour] = (horaMap[p.hour] || 0) + 1;
  }});
  let bestHora = -1, bestHoraCnt = 0;
  Object.entries(horaMap).forEach(([h, cnt]) => {{
    if (cnt > bestHoraCnt) {{ bestHoraCnt = cnt; bestHora = parseInt(h); }}
  }});
  document.getElementById('ic-melhor-hora').textContent     = bestHora >= 0 ? bestHora + 'h' : '—';
  document.getElementById('ic-melhor-hora-sub').textContent = bestHora >= 0
    ? `${{bestHoraCnt}} posts publicados nesse horário`
    : 'Dados insuficientes';

  const sortedTs = filteredPosts.map(p => p.timestamp).filter(Boolean).sort();
  let freqSemana = 0;
  if (sortedTs.length >= 2) {{
    const span = (new Date(sortedTs[sortedTs.length - 1]) - new Date(sortedTs[0])) / 86400000 || 1;
    freqSemana = Math.round(filteredPosts.length / span * 7 * 10) / 10;
  }}
  document.getElementById('ic-freq').textContent     = freqSemana + 'x';
  document.getElementById('ic-freq-sub').textContent = 'Frequência média no período';

  const bestLikes = filteredPosts.reduce((b, p) => (!b || p.like_count > b.like_count) ? p : b, null);
  const bestReach = filteredPosts.reduce((b, p) => (!b || p.reach    > b.reach)    ? p : b, null);
  const bestSaved = filteredPosts.reduce((b, p) => (!b || p.saved    > b.saved)    ? p : b, null);
  document.getElementById('highlight-posts-container').innerHTML =
    postCard(bestLikes, 'Mais curtido') +
    postCard(bestReach, 'Maior alcance') +
    postCard(bestSaved, 'Mais salvo');

  const tipoRows = Object.entries(tiposMap)
    .sort((a, b) => jAvg(b[1].likes) - jAvg(a[1].likes))
    .map(([t, s]) => {{
      const reach = s.reach.length ? jAvg(s.reach) : '—';
      return `<tr>
        <td><span class="badge badge-${{t.toLowerCase()}}">${{t}}</span></td>
        <td>${{s.likes.length}}</td>
        <td>${{jAvg(s.likes)}}</td>
        <td>${{jAvg(s.comments)}}</td>
        <td>${{jAvg(s.shares)}}</td>
        <td>${{jAvg(s.saved)}}</td>
        <td>${{reach}}</td>
      </tr>`;
    }}).join('');
  document.getElementById('tipo-table-body').innerHTML = tipoRows;

  const dowRows = [0, 1, 2, 3, 4, 5, 6]
    .filter(d => dowMap[d])
    .map(d => {{
      const s  = dowMap[d];
      const hl = d === bestDow ? ' style="background:rgba(255,108,0,0.06)"' : '';
      return `<tr${{hl}}>
        <td>${{DOW_PT[d]}}</td>
        <td>${{s.count}}</td>
        <td>${{jAvg(s.likes)}}</td>
        <td>${{jAvg(s.comments)}}</td>
      </tr>`;
    }}).join('');
  document.getElementById('dow-table-body').innerHTML = dowRows;

  const recs = [];
  if (bestType !== '—')
    recs.push(`<strong>Tipo de conteúdo:</strong> ${{bestType}} tem a melhor média de curtidas (${{bestTypeAvg}}). Priorize esse formato.`);
  if (bestDow >= 0)
    recs.push(`<strong>Melhor dia para postar:</strong> ${{DOW_PT[bestDow]}} concentra os posts com maior engajamento (média ${{bestDowAvg}} curtidas, ${{dowMap[bestDow].count}} posts).`);
  const er = parseFloat(engRate);
  if (er < 1)
    recs.push(`<strong>Taxa de engajamento baixa (${{engRate}}%):</strong> Experimente posts interativos — perguntas, enquetes nos Stories, chamadas para ação nas legendas.`);
  else if (er >= 3)
    recs.push(`<strong>Taxa de engajamento excelente (${{engRate}}%):</strong> A audiência está respondendo bem. Mantenha a consistência de conteúdo.`);
  else
    recs.push(`<strong>Taxa de engajamento boa (${{engRate}}%):</strong> Para crescer, teste legendas com histórias reais da empresa e convite à interação.`);
  if (freqSemana > 0 && freqSemana < 2)
    recs.push(`<strong>Frequência de postagem (${{freqSemana}}x/semana):</strong> Contas que postam pelo menos 3-4x por semana crescem mais rápido no algoritmo.`);
  else if (freqSemana >= 5)
    recs.push(`<strong>Frequência de postagem (${{freqSemana}}x/semana):</strong> Volume alto. Garanta que a qualidade acompanha a quantidade.`);
  else if (freqSemana > 0)
    recs.push(`<strong>Frequência de postagem (${{freqSemana}}x/semana):</strong> Boa consistência. Experimente Reels para ampliar o alcance orgânico.`);
  document.getElementById('rec-list').innerHTML = recs.map(r => `<li class="rec-item">${{r}}</li>`).join('');

  document.getElementById('analise-footer').textContent =
    `Análise baseada em ${{filteredPosts.length}} posts · Atualizado em: ${{COLETADO_EM}}`;
}}

// ── Dashboard update ──────────────────────────────────────────────────────────
let currentDays          = 30;
let currentFilteredPosts = [];

function updateAllCharts(days) {{
  currentDays = days;
  const filteredPosts     = filterByDays(allPostsData,     days, 'timestamp');
  const filteredReach     = filterByDays(allReachData,     days, 'date');
  const filteredFollowers = filterByDays(allFollowersData, days, 'date');
  const sorted = [...filteredPosts].sort((a, b) => a.timestamp.localeCompare(b.timestamp));

  currentFilteredPosts = filteredPosts;

  timelineChart.data.labels           = sorted.map(p => p.timestamp);
  timelineChart.data.datasets[0].data = sorted.map(p => p.like_count);
  timelineChart.data.datasets[1].data = sorted.map(p => p.comments_count);
  timelineChart.update();

  const top5 = [...filteredPosts].sort((a, b) => b.like_count - a.like_count).slice(0, 5);
  top5Chart.data.labels           = top5.map(p => p.caption || 'sem legenda');
  top5Chart.data.datasets[0].data = top5.map(p => p.like_count);
  top5Chart._permalinks           = top5.map(p => p.permalink);
  top5Chart.update();

  const tiposMap = {{}};
  filteredPosts.forEach(p => {{
    if (!tiposMap[p.media_type]) tiposMap[p.media_type] = {{ likes: [], comments: [] }};
    tiposMap[p.media_type].likes.push(p.like_count);
    tiposMap[p.media_type].comments.push(p.comments_count);
  }});
  const tLabels = Object.keys(tiposMap);
  const avg = arr => arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length * 10) / 10 : 0;
  tiposChart.data.labels              = tLabels;
  tiposChart.data.datasets[0].data    = tLabels.map(t => avg(tiposMap[t].likes));
  tiposChart.data.datasets[1].data    = tLabels.map(t => avg(tiposMap[t].comments));
  tiposChart.update();

  const donutMap = {{}};
  filteredPosts.forEach(p => {{ donutMap[p.media_type] = (donutMap[p.media_type] || 0) + 1; }});
  donutChart.data.labels           = Object.keys(donutMap);
  donutChart.data.datasets[0].data = Object.values(donutMap);
  donutChart.update();

  const recent10 = [...sorted].slice(-10);
  sharesSavosChart.data.labels              = recent10.map(p => p.timestamp.slice(5));
  sharesSavosChart.data.datasets[0].data    = recent10.map(p => p.shares);
  sharesSavosChart.data.datasets[1].data    = recent10.map(p => p.saved);
  sharesSavosChart.update();

  alcanceChart.data.labels           = filteredReach.map(r => r.date);
  alcanceChart.data.datasets[0].data = filteredReach.map(r => r.value);
  alcanceChart.update();

  seguidoresChart.data.labels           = filteredFollowers.map(r => r.date);
  seguidoresChart.data.datasets[0].data = filteredFollowers.map(r => r.value);
  seguidoresChart.update();

  if (document.getElementById('tab-analise').classList.contains('active')) {{
    updateAnalysis(filteredPosts);
  }}
}}

// ── Filter button wiring ──────────────────────────────────────────────────────
document.querySelectorAll('.filter-period-btn').forEach(btn => {{
  btn.addEventListener('click', function() {{
    document.querySelectorAll('.filter-period-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    updateAllCharts(parseInt(this.dataset.days, 10));
  }});
}});

// Initial render (30 days)
updateAllCharts(30);
renderHashtagAreas();
</script>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard salvo em {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    gerar_dashboard()
