#!/usr/bin/env python3
"""
Incrementum Places — Bulk Insert para Supabase

Uso:
  python3 scripts/bulk-insert-supabase.py

Insere os 261 restaurantes do migration-supabase.json na tabela Supabase.
"""
import json
import requests
from pathlib import Path

URL = "https://oziequrhypzbfdynnnda.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96aWVxdXJoeXB6YmZkeW5ubmRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQwNTU3OTEsImV4cCI6MjA4OTYzMTc5MX0.dU0_ISLUdDVAh0XQ4wLFlDXf4ZTOuRh__4_mcp0aFxo"

headers = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def main():
    json_path = Path(__file__).parent.parent / "data" / "migration-supabase.json"
    with open(json_path) as f:
        restaurants = json.load(f)
    
    print(f"Inserindo {len(restaurants)} restaurantes...")
    
    # Inserir em batches de 50
    batch_size = 50
    for i in range(0, len(restaurants), batch_size):
        batch = restaurants[i:i+batch_size]
        r = requests.post(
            f"{URL}/rest/v1/restaurants",
            headers=headers,
            json=batch,
            timeout=30
        )
        if r.status_code in (200, 201):
            print(f"  Batch {i//batch_size + 1}: OK ({len(batch)} items)")
        else:
            print(f"  Batch {i//batch_size + 1}: ERRO {r.status_code} - {r.text[:200]}")
            break
    
    print("\nDone.")

if __name__ == "__main__":
    main()
