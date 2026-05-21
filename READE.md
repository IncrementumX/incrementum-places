# Incrementum Places

## Reconcile Flow

Quando o estado do Safari/iPhone divergir do codigo-fonte:

1. Abra o site no iPhone/Safari
2. Clique o botao ⬇ (Exportar JSON) no header
3. Envie o arquivo .json para o repositorio
4. Rode: python3 scripts/reconcile-restaurants.py <arquivo>.json
5. Revisar: git diff index.html
6. Commit + push

O script regenera o _RAW removendo os deletados localmente.
Backup automatico do index.html anterior.

