#!/usr/bin/env python3
"""
Incrementum Places — Auto-detecta quando tabelas Supabase são criadas e executa bulk insert.

Uso:
  python3 scripts/wait-for-tables.py

Fica polling a cada 30s até detectar que a tabela 'restaurants' existe, então executa bulk insert.
"""
import time
import requests
import subprocess
import sys
from pathlib import Path

URL = "https://oziequrhypzbfdynnnda.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96aWVxdXJoeXB6YmZkeW5ubmRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQwNTU3OTEsImV4cCI6MjA4OTYzMTc5MX0.dU0_ISLUdDVAh0XQ4wLFlDXf4ZTOuRh__4_mcp0aFxo"

headers = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
}

def check_tables():
    r = requests.get(f"{URL}/rest/v1/restaurants?limit=1", headers=headers, timeout=10)
    return r.status_code == 200

def run_bulk_insert():
    script = Path(__file__).parent / "bulk-insert-supabase.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
    return result.returncode == 0

def main():
    print("Polling Supabase para detectar quando as tabelas são criadas...")
    print("(Ctrl+C para cancelar)")
    
    while True:
        if check_tables():
            print("\n✅ Tabela 'restaurants' detectada! Executando bulk insert...")
            if run_bulk_insert():
                print("\n🎉 Bulk insert completo! O app agora usa Supabase como source of truth.")
                break
            else:
                print("\n❌ Bulk insert falhou. Tente manualmente:")
                print("  python3 scripts/bulk-insert-supabase.py")
                break
        else:
            print("  Tabelas ainda não existem... aguardando 30s")
            time.sleep(30)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.")
