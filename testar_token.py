import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
USER_ID = os.getenv("INSTAGRAM_USER_ID", "17841404638923638")
BASE_URL = "https://graph.facebook.com/v19.0"

print("=== Testando token ===\n")

# 0. Debug do token
print("0. Debug do token lido do .env:")
print(f"   Tamanho: {len(TOKEN)} caracteres")
print(f"   Início: {TOKEN[:20] if TOKEN else 'VAZIO'}")
print(f"   Fim: {TOKEN[-20:] if TOKEN else 'VAZIO'}")
print(f"   Tem espaços? {' ' in TOKEN if TOKEN else 'N/A'}")
print(f"   Tem quebra de linha? {'\\n' in TOKEN or '\\r' in TOKEN if TOKEN else 'N/A'}")
print()

# Limpar token de caracteres indesejados
TOKEN_LIMPO = TOKEN.strip().strip('"').strip("'") if TOKEN else ""
print(f"   Token limpo (tamanho): {len(TOKEN_LIMPO)}")
print()

# 1. Verificar validade do token
print("1. Verificando token...")
r = requests.get(f"https://graph.facebook.com/debug_token", params={
    "input_token": TOKEN_LIMPO,
    "access_token": TOKEN_LIMPO
})
print(r.text)
print()

# 2. Teste simples na conta
print("2. Buscando perfil (só id e username)...")
r2 = requests.get(f"{BASE_URL}/{USER_ID}", params={
    "fields": "id,username",
    "access_token": TOKEN_LIMPO
})
print(r2.text)
print()

# 3. Ver qual conta está associada ao token
print("3. Verificando /me...")
r3 = requests.get(f"{BASE_URL}/me", params={"access_token": TOKEN_LIMPO})
print(r3.text)
