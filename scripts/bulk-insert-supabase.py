#!/usr/bin/env python3
"""
Incrementum Places — Bulk Insert para Supabase (normalizado)

Uso:
  python3 scripts/bulk-insert-supabase.py

Insere os 261 restaurantes do migration-supabase.json na tabela Supabase,
garantindo que todos os objetos tenham as mesmas chaves.
"""
import json
import requests
from pathlib import Path

URL = "https://oziequrhypzbfdynnnda.supabase.co"
# Use service_role key to bypass RLS for bulk insert
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96aWVxdXJoeXB6YmZkeW5ubmRhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDA1NTc5MSwiZXhwIjoyMDg5NjMxNzkxfQ.V5HaowRQQiI6SHU3nYWvcEKCw-tuOuMQsn4cnjDlrLg"

headers = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

def normalize_record(r):
    """Garante que todas as chaves existam, preenchendo com null."""
    all_keys = [
        "name", "neighborhood", "cuisine", "type", "chef", "price",
        "michelin", "bib", "latam50", "world50", "status", "occasions",
        "vibe", "instagram", "phone", "website", "reservation", "notes",
        "city", "is_builtin"
    ]
    return {k: r.get(k) for k in all_keys}

def main():
    json_path = Path(__file__).parent.parent / "data" / "migration-supabase.json"
    with open(json_path) as f:
        restaurants = json.load(f)
    
    # Normaliza todos os registros
    normalized = [normalize_record(r) for r in restaurants]
    
    print(f"Inserindo {len(normalized)} restaurantes...")
    
    # Inserir em batches de 50
    batch_size = 50
    for i in range(0, len(normalized), batch_size):
        batch = normalized[i:i+batch_size]
        r = requests.post(
            f"{URL}/rest/v1/restaurants",
            headers=headers,
            json=batch,
            timeout=30
        )
        if r.status_code in (200, 201):
            print(f"  Batch {i//batch_size + 1}: OK ({len(batch)} items)")
        else:
            print(f"  Batch {i//batch_size + 1}: ERRO {r.status_code} - {r.text[:300]}")
            break
    
    print("\nDone.")

if __name__ == "__main__":
    main()
