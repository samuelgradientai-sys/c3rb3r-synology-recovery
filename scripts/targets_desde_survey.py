#!/usr/bin/env python3
"""Genera targets.tsv para c3r_carve.py a partir del survey.jsonl.gz de c3r_btrfs.py.

Uso:
  python3 targets_desde_survey.py survey.jsonl.gz > targets.tsv
  python3 targets_desde_survey.py survey.jsonl.gz --detalle > detalle.txt   # qué archivos se incluyen

Solo entran archivos que:
  - quedaron en estado 'no_candidate' o 'partial' (los 'exact' se recuperan por la via normal),
  - tienen extensión con firma que el carving sabe buscar,
  - pesan 16 MiB o menos (por encima, C3RB3R no los cifra enteros y el carving no aplica).

La salida son pares únicos "tipo<TAB>tamaño_original": el carving solo acepta un candidato si su
longitud coincide EXACTA con el tamaño original anotado en el footer del .L0CK3D.
"""
import gzip, json, sys, collections

KIND = {
    'pdf': 'pdf',
    'jpg': 'jpg', 'jpeg': 'jpg',
    'png': 'png',
    'bmp': 'bmp',
    'doc': 'ole', 'xls': 'ole', 'ppt': 'ole',
    'docx': 'zip', 'xlsx': 'zip', 'xlsm': 'zip', 'pptx': 'zip', 'ppsx': 'zip',
    'odt': 'zip', 'ods': 'zip', 'odp': 'zip', 'zip': 'zip',
}
LIMITE = 16 * 1024 * 1024


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    src = sys.argv[1]
    detalle = '--detalle' in sys.argv[2:]
    pares, por_tipo, incluidos = set(), collections.Counter(), []

    with gzip.open(src, 'rt', encoding='utf-8', errors='replace') as f:
        for linea in f:
            try:
                r = json.loads(linea)
            except Exception:
                continue
            if r.get('status') not in ('no_candidate', 'partial'):
                continue
            ruta = r.get('path') or ''
            ext = ruta.rsplit('.L0CK3D', 1)[0].rsplit('.', 1)[-1].lower()
            tipo = KIND.get(ext)
            tam = r.get('orig') or 0
            if not tipo or not tam or tam > LIMITE:
                continue
            pares.add((tipo, tam))
            por_tipo[tipo] += 1
            incluidos.append((tipo, tam, r.get('status'), ruta))

    for tipo, tam in sorted(pares):
        print(f"{tipo}\t{tam}")

    if detalle:
        print(f"\n# {len(incluidos)} archivos -> {len(pares)} pares tipo/tamaño", file=sys.stderr)
        for tipo, tam, est, ruta in sorted(incluidos, key=lambda x: -x[1]):
            print(f"# {tam:>10}  {tipo:<4} {est:<13} {ruta}", file=sys.stderr)
        print("# por tipo: " + ", ".join(f"{k}={v}" for k, v in por_tipo.most_common()), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
