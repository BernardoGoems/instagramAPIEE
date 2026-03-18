import requests

# Cole o token COMPLETO aqui entre as aspas:
TOKEN = "COLE_SEU_TOKEN_AQUI"

USER_ID = "17841404638923638"
BASE_URL = "https://graph.facebook.com/v19.0"

print(f"Tamanho do token: {len(TOKEN)}")
print(f"Início: {TOKEN[:30]}")
print(f"Fim: {TOKEN[-20:]}")
print()

r = requests.get(f"{BASE_URL}/{USER_ID}", params={
    "fields": "id,username,followers_count",
    "access_token": TOKEN
})
print(r.status_code)
print(r.text)
