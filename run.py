from coletar_dados import main as coletar
from gerar_dashboard import gerar_dashboard
import webbrowser

print("=== Dashboard Instagram @engehalleletrica ===\n")
coletar()
gerar_dashboard()
webbrowser.open("dashboard.html")
print("\nDashboard aberto no navegador!")
