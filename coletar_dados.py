import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
USER_ID = os.getenv("INSTAGRAM_USER_ID", "17841404638923638")
BASE_URL = "https://graph.facebook.com/v22.0"


def get(endpoint, params={}):
    params["access_token"] = TOKEN
    r = requests.get(f"{BASE_URL}{endpoint}", params=params)
    if not r.ok:
        print(f"Erro {r.status_code}: {r.text}")
        r.raise_for_status()
    return r.json()


def coletar_perfil():
    data = get(f"/{USER_ID}", {"fields": "name,username,followers_count,follows_count,media_count,profile_picture_url,biography,website"})
    return data


def coletar_insights_conta():
    """Coleta insights da conta em janelas de 30 dias (limite da API).
    Faz 3 chamadas consecutivas para cobrir 90 dias no total.
    """
    hoje = datetime.now()
    metricas_merge = {}

    # API limita a 30 dias por chamada — coleta 3 janelas para cobrir 90 dias de reach.
    # follower_count só suporta os últimos 30 dias (janela 0).
    for i in range(3):
        until = int((hoje - timedelta(days=30 * i)).timestamp())
        since = int((hoje - timedelta(days=30 * (i + 1))).timestamp())
        metricas = "reach,follower_count" if i == 0 else "reach"
        try:
            data = get(f"/{USER_ID}/insights", {
                "metric": metricas,
                "period": "day",
                "since": since,
                "until": until,
            })
            for m in data.get("data", []):
                nome = m["name"]
                if nome not in metricas_merge:
                    metricas_merge[nome] = {k: v for k, v in m.items() if k != "values"}
                    metricas_merge[nome]["values"] = []
                # Prepend valores mais antigos para manter ordem cronológica
                metricas_merge[nome]["values"] = m.get("values", []) + metricas_merge[nome]["values"]
        except Exception:
            print(f"  Aviso: janela {i+1}/3 — não foi possível coletar reach.")

    resultado = list(metricas_merge.values())

    # profile_views e accounts_engaged: apenas últimos 30 dias (exigem metric_type=total_value)
    since30 = int((hoje - timedelta(days=30)).timestamp())
    until30 = int(hoje.timestamp())
    try:
        data = get(f"/{USER_ID}/insights", {
            "metric": "profile_views,accounts_engaged",
            "period": "day",
            "metric_type": "total_value",
            "since": since30,
            "until": until30,
        })
        resultado += data.get("data", [])
    except Exception:
        print("  Aviso: não foi possível coletar profile_views/accounts_engaged.")

    return resultado


def coletar_posts(limite=50):  # 50 posts para ter histórico suficiente para o filtro
    data = get(f"/{USER_ID}/media", {
        "fields": "id,caption,media_type,timestamp,like_count,comments_count,thumbnail_url,media_url,permalink",
        "limit": limite
    })
    return data.get("data", [])


def coletar_insights_post(post_id, media_type):
    # API v22+: impressions removido; video_views substituído por views
    if media_type in ("VIDEO", "REEL"):
        metricas = "reach,likes,comments,shares,saved,views,total_interactions"
    else:
        metricas = "reach,likes,comments,shares,saved,total_interactions"
    try:
        data = get(f"/{post_id}/insights", {"metric": metricas})
        return {item["name"]: item["values"][0]["value"] for item in data.get("data", [])}
    except Exception:
        return {}



def main():
    print("Coletando dados do Instagram @engehalleletrica...")

    perfil = coletar_perfil()
    insights_conta = coletar_insights_conta()
    posts = coletar_posts()

    posts_com_insights = []
    for post in posts:
        insights = coletar_insights_post(post["id"], post.get("media_type", "IMAGE"))
        posts_com_insights.append({**post, "insights": insights})
        print(f"  Post coletado: {post['id']}")

    resultado = {
        "coletado_em": datetime.now().isoformat(),
        "perfil": perfil,
        "insights_conta": insights_conta,
        "posts": posts_com_insights,
    }

    with open("dados_instagram.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print("Dados salvos em dados_instagram.json")
    return resultado


if __name__ == "__main__":
    main()
