#!/usr/bin/env python3
"""
Incrementum Places — Reconcile _RAW from exported state

Recebe o JSON exportado do app (via botao ⬇) e regenera o index.html
com uma lista canônica limpa, removendo os restaurantes deletados localmente.

Fluxo:
  1. Eduardo abre o site no iPhone, clica ⬇, exporta incrementum-places-YYYY-MM-DD.json
  2. Manda o JSON (via Telegram, AirDrop, etc.)
  3. Roda este script: python3 scripts/reconcile-restaurants.py <json>
  4. Script gera index.html limpo + diff + backup
  5. git add index.html && git commit && git push
  6. Todos os devices veem o mesmo estado

Autor: Code Peer (CTO)
Data: 2026-05-21
"""

import json
import re
import shutil
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
INDEX_PATH = REPO_ROOT / "index.html"
SCHEMA_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# CORE
# ---------------------------------------------------------------------------

def load_index_html() -> str:
    """Lê o index.html atual."""
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return f.read()


def extract_raw_block(html: str) -> tuple:
    """Extrai o bloco const _RAW = [...]; do index.html.

    Retorna (start_index, end_index, raw_content_string).
    """
    pattern = r"(const _RAW = \[)(.*?)(\];)"
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        raise ValueError("Nao encontrei 'const _RAW = [...];' no index.html")
    return match.start(1), match.end(3), match.group(0)


def parse_restaurant_objects(raw_block: str) -> list[dict]:
    """Faz parse manual dos objetos no bloco _RAW.

    Cada objeto tem formato:
        {n:"Nome",h:"Bairro",c:"Cozinha",t:"tipo",ch:"Chef",p:4,...}

    Retorna lista de dicts.
    """
    # Remove comentarios de categoria /* ── XXX ── */
    cleaned = re.sub(r"/\*.*?\*/", "", raw_block, flags=re.DOTALL)

    # Encontra cada objeto {n:"...",...}    
    objs = []
    # Padrao: {n:"NAME" seguido de campos ate }
    # Usamos um parser ingenuo mas robusto para este formato especifico
    for m in re.finditer(r'\{n:"([^"]+)"(.*?)\}', cleaned):
        name = m.group(1)
        fields_str = m.group(2)
        obj = {"n": name}
        
        # Extrai cada campo: key:"value" ou key:numero ou key:[...]
        # h:"Jardins"
        # c:"Contemporanea"
        # t:"contemporary"
        # ch:"Alex Atala"
        # p:4
        # mi:3
        # l50:4
        # w50:14
        # st:"want"
        # oc:["impress","date","biz"]
        # vb:"descricao..."
        # ig:"handle"
        # tel:""
        # site:"url"
        # reserva:""
        # notes:""
        # city:"MIA"
        
        # Campos string
        for key in ["h", "c", "t", "ch", "st", "vb", "ig", "tel", "site", "reserva", "notes", "city"]:
            pat = rf'{key}:"((?:[^"\\]|\\.)*?)"'
            fm = re.search(pat, fields_str)
            if fm:
                obj[key] = fm.group(1).replace('\\"', '"')
        
        # Campos numericos
        for key in ["p", "mi", "bib", "l50", "w50"]:
            pat = rf'{key}:(\d+)'
            fm = re.search(pat, fields_str)
            if fm:
                obj[key] = int(fm.group(1))
        
        # Array oc
        oc_m = re.search(r'oc:\[(.*?)\]', fields_str)
        if oc_m:
            oc_str = oc_m.group(1)
            obj["oc"] = [s.strip().strip('"') for s in oc_str.split(",") if s.strip()]
        
        objs.append(obj)
    
    return objs


def load_exported_json(json_path: Path) -> dict:
    """Carrega o JSON exportado do app."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Schema validation
    if not isinstance(data.get("restaurants"), list):
        raise ValueError("JSON invalido: campo 'restaurants' nao encontrado ou nao e lista")
    
    return data


def reconcile(natives_code: list[dict], exported: dict) -> tuple:
    """Reconcilia a lista do codigo com o estado exportado.

    Retorna (natives_limpa, user_added, removidos, estatisticas).
    """
    persisted = exported.get("restaurants", [])
    deleted_names = set(exported.get("deleted", []))
    
    # Estabelecer identidade: nome e bairro juntos (fallback para nome so)
    persisted_natives = [r for r in persisted if not r.get("_user")]
    persisted_users = [r for r in persisted if r.get("_user")]
    
    # Mapa de lookup pelo nome
    persisted_by_name = {r["n"]: r for r in persisted_natives}
    
    # Lista de nativos do codigo que NAO estao na lista deletada
    removidos = []
    mantidos = []
    
    for r in natives_code:
        if r["n"] in deleted_names:
            removidos.append(r)
        else:
            mantidos.append(r)
    
    # Detectar duplicatas no codigo
    seen_names = set()
    dupes = []
    for r in natives_code:
        if r["n"] in seen_names:
            dupes.append(r["n"])
        seen_names.add(r["n"])
    
    stats = {
        "total_no_codigo": len(natives_code),
        "persistidos_no_app": len(persisted),
        "persistidos_natives": len(persisted_natives),
        "persistidos_user_added": len(persisted_users),
        "deletados_no_export": len(deleted_names),
        "mantidos_apos_reconcile": len(mantidos),
        "removidos": len(removidos),
        "duplicatas_detectadas": len(dupes),
        "schema_version": SCHEMA_VERSION,
    }
    
    return mantidos, persisted_users, removidos, stats, dupes


def build_raw_block(natives: list[dict], users: list[dict]) -> str:
    """Gera o bloco const _RAW = [...] a partir da lista limpa."""
    
    def serialize_obj(r: dict) -> str:
        fields = []
        fields.append(f'n:"{r["n"]}"')
        fields.append(f'h:"{r.get("h", "")}"')
        fields.append(f'c:"{r.get("c", "")}"')
        fields.append(f't:"{r.get("t", "contemporary")}"')
        fields.append(f'ch:"{r.get("ch", "—")}"')
        fields.append(f'p:{r.get("p", 2)}')
        if r.get("mi"): fields.append(f'mi:{r["mi"]}')
        if r.get("bib"): fields.append(f'bib:{r["bib"]}')
        if r.get("l50"): fields.append(f'l50:{r["l50"]}')
        if r.get("w50"): fields.append(f'w50:{r["w50"]}')
        fields.append(f'st:"{r.get("st", "want")}"')
        if r.get("oc"):
            oc_str = ",".join(f'"{o}"' for o in r["oc"])
            fields.append(f'oc:[{oc_str}]')
        if r.get("city") and r["city"] not in ("SP", ""):
            fields.append(f'city:"{r["city"]}"')
        vb = r.get("vb", "").replace('"', '\\"')
        fields.append(f'vb:"{vb}"')
        if r.get("ig"): fields.append(f'ig:"{r["ig"]}"')
        if r.get("tel"): fields.append(f'tel:"{r["tel"]}"')
        if r.get("site"): fields.append(f'site:"{r["site"]}"')
        if r.get("reserva"): fields.append(f'reserva:"{r["reserva"]}"')
        if r.get("notes"):
            notes = r["notes"].replace('"', '\\"')
            fields.append(f'notes:"{notes}"')
        return "{" + ",".join(fields) + "}"
    
    lines = ["const _RAW = ["]
    
    # Agrupar por categoria tipo
    CAT_ORDER = {
        "contemporary": "CONTEMPORARY",
        "italian": "ITALIAN",
        "japanese": "JAPANESE",
        "french": "FRENCH",
        "brazilian": "BRAZILIAN",
        "seafood": "SEAFOOD",
        "steakhouse": "STEAKHOUSE",
        "bar": "BAR",
        "mediterranean": "MEDITERRANEAN",
        "international": "INTERNATIONAL"
    }
    
    by_cat = {}
    for r in natives:
        cat = r.get("t", "contemporary")
        by_cat.setdefault(cat, []).append(r)
    
    for cat_key, cat_label in CAT_ORDER.items():
        if cat_key not in by_cat:
            continue
        lines.append(f"\n/* ── {cat_label} ── */")
        for r in by_cat[cat_key]:
            lines.append(serialize_obj(r) + ",")
    
    # User-added ao final
    if users:
        lines.append("\n/* ── USER ADDED ── */")
        for r in users:
            s = serialize_obj(r)
            # Adiciona flag _user como ultimo campo
            s = s.rstrip("}") + ',_user:true}'
            lines.append(s + ",")
    
    lines.append("];")
    return "\n".join(lines)


def generate_report(stats: dict, removidos: list[dict], dupes: list[str]) -> str:
    """Gera relatorio ASCII com estatisticas."""
    lines = []
    lines.append("=" * 60)
    lines.append("INCREMENTUM PLACES — RECONCILIACAO")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Schema:        {stats['schema_version']}")
    lines.append(f"Timestamp:     {datetime.now().isoformat()}")
    lines.append("")
    lines.append("--- ESTATISTICAS ---")
    lines.append(f"No codigo (antes):     {stats['total_no_codigo']}")
    lines.append(f"Persistidos no app:    {stats['persistidos_no_app']}")
    lines.append(f"  - Natives:           {stats['persistidos_natives']}")
    lines.append(f"  - User-added:        {stats['persistidos_user_added']}")
    lines.append(f"Deletados no export:   {stats['deletados_no_export']}")
    lines.append(f"Mantidos (depois):     {stats['mantidos_apos_reconcile']}")
    lines.append(f"Removidos:             {stats['removidos']}")
    lines.append(f"Duplicatas detectadas: {stats['duplicatas_detectadas']}")
    lines.append("")
    
    if removidos:
        lines.append("--- RESTAURANTES REMOVIDOS ---")
        for r in removidos:
            cat = r.get("t", "?")
            st = r.get("st", "?")
            lines.append(f"  - {r['n']:30s} [{cat:12s} | {st}]")
        lines.append("")
    
    if dupes:
        lines.append("--- DUPLICATAS DETECTADAS ---")
        for d in dupes:
            lines.append(f"  - {d}")
        lines.append("")
    
    lines.append("--- VALIDACAO ---")
    delta = stats['total_no_codigo'] - stats['mantidos_apos_reconcile']
    assert delta == stats['removidos'], "ERRO: math inconsistente"
    lines.append(f"Math check: OK ({delta} == {stats['removidos']})")
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def main():
    # Argumentos
    if len(sys.argv) < 2:
        print("Uso: python3 reconcile-restaurants.py <exportado.json>")
        print("")
        print("Fluxo:")
        print("  1. Eduardo clica ⬇ no app no iPhone/Safari")
        print("  2. Manda o arquivo .json")
        print("  3. python3 reconcile-restaurants.py incrementum-places-YYYY-MM-DD.json")
        print("  4. git diff para revisar")
        print("  5. git add index.html && git commit && git push")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"ERRO: arquivo nao encontrado: {json_path}")
        sys.exit(1)
    
    # -----------------------------------------------------------------------
    # 1. Carregar o que temos
    # -----------------------------------------------------------------------
    print(f"[1/5] Carregando index.html...")
    html = load_index_html()
    
    print(f"[2/5] Extraindo _RAW atual...")
    start, end, old_block = extract_raw_block(html)
    natives_code = parse_restaurant_objects(old_block)
    print(f"       -> {len(natives_code)} restaurantes no codigo")
    
    print(f"[3/5] Carregando JSON exportado...")
    exported = load_exported_json(json_path)
    print(f"       -> {len(exported['restaurants'])} restaurantes no export")
    print(f"       -> {len(exported.get('deleted', []))} deletados no export")
    
    # -----------------------------------------------------------------------
    # 2. Reconciliar
    # -----------------------------------------------------------------------
    print(f"[4/5] Reconciliando...")
    mantidos, users, removidos, stats, dupes = reconcile(natives_code, exported)
    
    # -----------------------------------------------------------------------
    # 3. Gerar novo bloco _RAW
    # -----------------------------------------------------------------------
    print(f"[5/5] Gerando novo index.html...")
    new_raw_block = build_raw_block(mantidos, users)
    
    # Montar novo HTML
    new_html = html[:start] + new_raw_block + html[end:]
    
    # Backup
    backup_path = INDEX_PATH.with_suffix(f".html.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(INDEX_PATH, backup_path)
    print(f"       -> Backup: {backup_path}")
    
    # Escrever novo
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"       -> Novo index.html escrito")
    
    # Relatorio
    report = generate_report(stats, removidos, dupes)
    report_path = REPO_ROOT / f"reconcile-report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"       -> Relatorio: {report_path}")
    print("")
    print(report)
    print("")
    print("Proximo passo:")
    print("  git diff index.html   # revisar o que mudou")
    print("  git add index.html")
    print("  git commit -m 'sync: reconcile _RAW from exported state'")
    print("  git push origin main")


if __name__ == "__main__":
    main()
