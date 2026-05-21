#!/usr/bin/env python3
"""
Incrementum Places — Migração: _RAW → Supabase

Extrai os restaurantes do index.html e gera:
  1. JSON para bulk insert na API REST do Supabase
  2. SQL INSERT statements (fallback)

Uso:
  python3 scripts/migrate-to-supabase.py

Output:
  data/migration-supabase.json  — array de objetos pronto para POST
  data/migration-supabase.sql   — INSERT statements

Próximo passo: usar Supabase Dashboard → SQL Editor para rodar o schema.sql,
depois Table Editor → Import para subir o JSON.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_PATH = REPO_ROOT / "index.html"
OUTPUT_DIR = REPO_ROOT / "data"

def extract_raw():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    match = re.search(r'const _RAW = \[(.*?)\];', html, re.DOTALL)
    if not match:
        raise ValueError("Não encontrei const _RAW no index.html")
    
    raw_block = match.group(1)
    # Remove comentários de categoria
    cleaned = re.sub(r"/\*.*?\*/", "", raw_block, flags=re.DOTALL)
    
    restaurants = []
    for m in re.finditer(r'\{n:"([^"]+)"(.*?)\}', cleaned):
        name = m.group(1)
        fields_str = m.group(2)
        
        obj = {
            "name": name,
            "neighborhood": "",
            "cuisine": "",
            "type": "contemporary",
            "chef": "—",
            "price": 2,
            "michelin": None,
            "bib": None,
            "latam50": None,
            "world50": None,
            "status": "want",
            "occasions": [],
            "vibe": "",
            "instagram": "",
            "phone": "",
            "website": "",
            "reservation": "",
            "notes": "",
            "city": "SP",
            "is_builtin": True
        }
        
        # String fields
        for key in ["h", "c", "t", "ch", "st", "vb", "ig", "tel", "site", "reserva", "notes", "city"]:
            pat = rf'{key}:"((?:[^"\\]|\\.)*?)"'
            fm = re.search(pat, fields_str)
            if fm:
                val = fm.group(1).replace('\\"', '"')
                # Map field names
                if key == "h": obj["neighborhood"] = val
                elif key == "c": obj["cuisine"] = val
                elif key == "t": obj["type"] = val
                elif key == "ch": obj["chef"] = val or "—"
                elif key == "st": obj["status"] = val
                elif key == "vb": obj["vibe"] = val
                elif key == "ig": obj["instagram"] = val
                elif key == "tel": obj["phone"] = val
                elif key == "site": obj["website"] = val
                elif key == "reserva": obj["reservation"] = val
                elif key == "notes": obj["notes"] = val
                elif key == "city": obj["city"] = val or "SP"
        
        # Numeric fields
        for key in ["p", "mi", "bib", "l50", "w50"]:
            pat = rf'{key}:(\d+)'
            fm = re.search(pat, fields_str)
            if fm:
                val = int(fm.group(1))
                if key == "p": obj["price"] = val
                elif key == "mi": obj["michelin"] = val
                elif key == "bib": obj["bib"] = val
                elif key == "l50": obj["latam50"] = val
                elif key == "w50": obj["world50"] = val
        
        # Array oc
        oc_m = re.search(r'oc:\[(.*?)\]', fields_str)
        if oc_m:
            oc_str = oc_m.group(1)
            obj["occasions"] = [s.strip().strip('"') for s in oc_str.split(",") if s.strip()]
        
        # Clean None fields for compact JSON
        obj_clean = {k: v for k, v in obj.items() if v is not None and v != "" and v != []}
        if obj["chef"] != "—":
            obj_clean["chef"] = obj["chef"]
        if obj["city"] != "SP":
            obj_clean["city"] = obj["city"]
        
        restaurants.append(obj_clean)
    
    return restaurants

def generate_sql(restaurants):
    lines = ["-- Auto-generated migration"]
    lines.append(f"-- {len(restaurants)} restaurants")
    lines.append("")
    
    for r in restaurants:
        cols = []
        vals = []
        for k, v in r.items():
            if v is None:
                continue
            cols.append(k)
            if isinstance(v, str):
                escaped = v.replace("'", "''")
                vals.append(f"'{escaped}'")
            elif isinstance(v, bool):
                vals.append(str(v).lower())
            elif isinstance(v, list):
                arr = ",".join(f'"{x}"' for x in v)
                vals.append(f"'{{{arr}}}'")
            else:
                vals.append(str(v))
        
        lines.append(f"INSERT INTO restaurants ({', '.join(cols)}) VALUES ({', '.join(vals)});")
    
    return "\n".join(lines)

def main():
    print("[1/4] Extraindo restaurantes do index.html...")
    restaurants = extract_raw()
    print(f"       -> {len(restaurants)} restaurantes extraídos")
    
    print("[2/4] Gerando JSON para Supabase...")
    OUTPUT_DIR.mkdir(exist_ok=True)
    json_path = OUTPUT_DIR / "migration-supabase.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(restaurants, f, indent=2, ensure_ascii=False)
    print(f"       -> {json_path}")
    
    print("[3/4] Gerando SQL fallback...")
    sql_path = OUTPUT_DIR / "migration-supabase.sql"
    sql = generate_sql(restaurants)
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"       -> {sql_path}")
    
    print("[4/4] Validação...")
    assert len(restaurants) >= 200, f"ERRO: só extraiu {len(restaurants)} restaurantes"
    names = [r["name"] for r in restaurants]
    assert len(names) == len(set(names)), f"ERRO: duplicatas detectadas"
    print(f"       -> OK: {len(restaurants)} restaurantes, sem duplicatas")
    print("")
    print("Proximo passo:")
    print("  1. Crie o projeto em https://supabase.com")
    print("  2. Dashboard → SQL Editor: cole schema.sql e rode")
    print("  3. Dashboard → Table Editor → restaurants → Import: suba migration-supabase.json")
    print("  4. Pegue Project URL + anon key (Settings → API)")
    print("  5. Atualize index.html com as credenciais")

if __name__ == "__main__":
    main()
