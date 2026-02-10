#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "numpy>=2.0.0",
#   "scikit-learn>=1.5.0",
#   "sentence-transformers>=3.0.0",
# ]
# ///

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.manifold import TSNE


HTML_TEMPLATE = """<!doctype html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Mercadona en 2D</title>
  <link rel=\"icon\" href=\"data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20100%20100'%3E%3Ctext%20y='.9em'%20font-size='90'%3E%F0%9F%8D%8D%3C/text%3E%3C/svg%3E\" />
  <style>
    html, body { height: 100%; margin: 0; }
    body { overflow: hidden; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; color: #111; }

    #deck-canvas { position: fixed; inset: 0; }

    #hud {
      position: fixed;
      top: 12px;
      left: 12px;
      width: 320px;
      max-height: calc(100vh - 24px);
      overflow: auto;
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid rgba(0,0,0,0.08);
      border-radius: 10px;
      padding: 10px 10px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.12);
      backdrop-filter: blur(6px);
    }

    #title { font-weight: 650; font-size: 14px; margin: 0 0 8px 0; }
    #subtitle { font-size: 12px; color: #444; margin: 0 0 10px 0; line-height: 1.25; }

    #search {
      width: 100%;
      box-sizing: border-box;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid rgba(0,0,0,0.14);
      outline: none;
      font-size: 13px;
      margin-bottom: 10px;
    }

    #legend { display: grid; grid-template-columns: 14px 1fr auto; gap: 8px 10px; align-items: center; }
    .swatch { width: 12px; height: 12px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.15); }
    .cat { font-size: 12px; color: #222; }
    .count { font-variant-numeric: tabular-nums; font-size: 12px; color: #555; }

    #stats { margin-top: 10px; font-size: 12px; color: #555; }

    #tooltip {
      position: fixed;
      pointer-events: none;
      display: none;
      max-width: 360px;
      background: rgba(17, 17, 17, 0.92);
      color: #fff;
      border-radius: 10px;
      padding: 10px;
      box-shadow: 0 14px 40px rgba(0,0,0,0.35);
    }

    #tooltip .name { font-size: 13px; font-weight: 650; margin-bottom: 4px; }
    #tooltip .meta { font-size: 12px; opacity: 0.88; line-height: 1.25; }
    #tooltip .row { display: grid; grid-template-columns: 54px 1fr; gap: 10px; align-items: start; }
    #tooltip img { width: 54px; height: 54px; object-fit: cover; border-radius: 8px; background: rgba(255,255,255,0.08); }

    a { color: inherit; }
  </style>
</head>
<body>
  <canvas id=\"deck-canvas\"></canvas>

  <div id=\"hud\">
    <div id=\"title\">Mercadona en 2D</div>
    <div id=\"subtitle\">Embedding 2D (t-SNE) a partir del texto del producto (nombre, descripción, categoría, marca). Pasa el ratón para ver detalles. Click para abrir el producto.</div>
    <input id=\"search\" placeholder=\"Buscar por nombre…\" autocomplete=\"off\" />
    <div id=\"legend\"></div>
    <div id=\"stats\"></div>
  </div>

  <div id=\"tooltip\"></div>

  <script id=\"points\" type=\"application/json\">__POINTS_JSON__</script>
  <script id=\"categories\" type=\"application/json\">__CATEGORIES_JSON__</script>

  <script src=\"https://unpkg.com/deck.gl@8.9.36/dist.min.js\"></script>
  <script>
    const POINTS = JSON.parse(document.getElementById('points').textContent);
    const CATEGORIES = JSON.parse(document.getElementById('categories').textContent);

    const elLegend = document.getElementById('legend');
    const elStats = document.getElementById('stats');
    const elSearch = document.getElementById('search');
    const elTooltip = document.getElementById('tooltip');

    function fmtEur(v) {
      if (v == null || Number.isNaN(v)) return '';
      return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(v);
    }

    function renderLegend() {
      elLegend.innerHTML = '';
      for (const c of CATEGORIES) {
        const sw = document.createElement('div');
        sw.className = 'swatch';
        sw.style.background = `rgb(${c.color[0]}, ${c.color[1]}, ${c.color[2]})`;

        const name = document.createElement('div');
        name.className = 'cat';
        name.textContent = c.name;

        const count = document.createElement('div');
        count.className = 'count';
        count.textContent = c.count;

        elLegend.appendChild(sw);
        elLegend.appendChild(name);
        elLegend.appendChild(count);
      }
    }

    function getFilteredPoints() {
      const q = (elSearch.value || '').trim().toLowerCase();
      if (!q) return POINTS;
      return POINTS.filter(p => (p.name || '').toLowerCase().includes(q));
    }

    function updateStats(filtered) {
      elStats.textContent = `${filtered.length.toLocaleString('es-ES')} / ${POINTS.length.toLocaleString('es-ES')} productos`;
    }

    function showTooltip({x, y, object}) {
      if (!object) {
        elTooltip.style.display = 'none';
        return;
      }

      const price = fmtEur(object.price);
      const category = object.top_category || '';

      elTooltip.innerHTML = `
        <div class="row">
          <img src="${object.thumbnail}" alt="" />
          <div>
            <div class="name">${object.name}</div>
            <div class="meta">${category}${price ? ` · ${price}` : ''}</div>
          </div>
        </div>
      `;

      const pad = 14;

      // Measure after making it visible.
      elTooltip.style.display = 'block';
      elTooltip.style.visibility = 'hidden';
      const rect = elTooltip.getBoundingClientRect();

      let left = x + 14;
      let top = y + 14;
      if (left + rect.width + pad > window.innerWidth) left = x - rect.width - 14;
      if (top + rect.height + pad > window.innerHeight) top = y - rect.height - 14;

      elTooltip.style.left = `${Math.max(pad, left)}px`;
      elTooltip.style.top = `${Math.max(pad, top)}px`;
      elTooltip.style.visibility = 'visible';
    }

    let hoveredId = null;
    let filteredPoints = getFilteredPoints();

    renderLegend();
    updateStats(filteredPoints);

    const layer = () => new deck.ScatterplotLayer({
      id: 'products',
      data: filteredPoints,
      pickable: true,
      coordinateSystem: deck.COORDINATE_SYSTEM.CARTESIAN,
      getPosition: d => [d.x, d.y],
      getRadius: d => (d.id === hoveredId ? 0.48 : 0.30),
      radiusUnits: 'common',
      radiusMinPixels: 1.6,
      radiusMaxPixels: 20,
      getFillColor: d => d.color,
      opacity: 0.9,
      onHover: info => {
        const nextHoveredId = info.object ? info.object.id : null;
        if (nextHoveredId !== hoveredId) {
          hoveredId = nextHoveredId;
          deckgl.setProps({ layers: [layer()] });
        }
        showTooltip(info);
      },
      onClick: info => {
        if (info.object && info.object.url) window.open(info.object.url, '_blank', 'noopener');
      }
    });

    function quantile(sorted, q) {
      if (!sorted.length) return 0;
      const pos = (sorted.length - 1) * q;
      const base = Math.floor(pos);
      const rest = pos - base;
      if (sorted[base + 1] === undefined) return sorted[base];
      return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
    }

    function computeInitialViewState(points) {
      const xs = points.map(p => p.x).filter(Number.isFinite).sort((a,b) => a-b);
      const ys = points.map(p => p.y).filter(Number.isFinite).sort((a,b) => a-b);
      if (!xs.length || !ys.length) return { target: [0,0,0], zoom: 0 };

      // Robust bounds to avoid outliers making the plot tiny.
      const x0 = quantile(xs, 0.01);
      const x1 = quantile(xs, 0.99);
      const y0 = quantile(ys, 0.01);
      const y1 = quantile(ys, 0.99);

      const w = Math.max(1e-6, x1 - x0);
      const h = Math.max(1e-6, y1 - y0);
      const cx = (x0 + x1) / 2;
      const cy = (y0 + y1) / 2;

      const pad = 0.85; // leave some breathing room
      const scale = pad * Math.min(window.innerWidth / w, window.innerHeight / h);
      const zoom = Math.log2(Math.max(1e-6, scale));

      return { target: [cx, cy, 0], zoom };
    }

    const deckgl = new deck.Deck({
      canvas: 'deck-canvas',
      views: new deck.OrthographicView({ id: 'ortho' }),
      controller: true,
      initialViewState: computeInitialViewState(POINTS),
      layers: [layer()]
    });

    let searchTimer = null;
    elSearch.addEventListener('input', () => {
      if (searchTimer) clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        filteredPoints = getFilteredPoints();
        updateStats(filteredPoints);
        deckgl.setProps({ layers: [layer()] });
      }, 80);
    });

    window.addEventListener('resize', () => {
      deckgl.setProps({});
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === '/' && document.activeElement !== elSearch) {
        e.preventDefault();
        elSearch.focus();
      }
      if (e.key === 'Escape' && document.activeElement === elSearch) {
        elSearch.value = '';
        filteredPoints = getFilteredPoints();
        updateStats(filteredPoints);
        deckgl.setProps({ layers: [layer()] });
        elSearch.blur();
      }
    });
  </script>
</body>
</html>
"""


_WS_RE = re.compile(r"\s+")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class ProductRecord:
    id: str
    name: str
    top_category: str
    category_path: str
    brand: str
    price: float
    thumbnail: str
    url: str
    text: str


def _clean_text(s: str | None) -> str:
    if not s:
        return ""
    s = _HTML_TAG_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def _iter_category_paths(categories: object) -> list[list[str]]:
    paths: list[list[str]] = []

    def walk(node: object, path: list[str]) -> None:
        if not isinstance(node, dict):
            return
        name = node.get("name")
        if isinstance(name, str) and name.strip():
            path = [*path, name.strip()]

        children = node.get("categories")
        if isinstance(children, list) and children:
            for child in children:
                walk(child, path)
        else:
            if path:
                paths.append(path)

    if isinstance(categories, list):
        for root in categories:
            walk(root, [])

    return paths


def _category_path_and_top(prod: dict) -> tuple[str, str]:
    paths = _iter_category_paths(prod.get("categories"))
    if not paths:
        return ("", "")

    # Prefer longest path, then stable tie-break.
    paths.sort(key=lambda p: (-len(p), " > ".join(p)))
    best = paths[0]
    top = best[0] if best else ""
    return (" > ".join(best), top)


def _product_to_record(prod: dict) -> ProductRecord:
    pid = str(prod.get("id") or "").strip()
    name = _clean_text(str(prod.get("display_name") or "").strip())

    details = prod.get("details")
    description = ""
    if isinstance(details, dict):
        description = _clean_text(details.get("description"))

    ingredients = ""
    ni = prod.get("nutrition_information")
    if isinstance(ni, dict):
        ingredients = _clean_text(ni.get("ingredients"))

    category_path, top_category = _category_path_and_top(prod)
    brand = _clean_text(prod.get("brand") if isinstance(prod.get("brand"), str) else "")

    price_raw = (prod.get("price_instructions") or {}).get("unit_price")
    price = float(price_raw) if price_raw is not None else math.nan

    thumbnail = str(prod.get("thumbnail") or "").strip()
    url = str(prod.get("share_url") or "").strip()

    parts: list[str] = []
    if name:
        parts.append(name)
    if description and description.lower() != name.lower():
        parts.append(description)
    if category_path:
        parts.append(f"Categoría: {category_path}.")
    if brand:
        parts.append(f"Marca: {brand}.")
    if ingredients:
        parts.append(f"Ingredientes: {ingredients[:400]}.")

    text = " ".join(parts)
    return ProductRecord(
        id=pid,
        name=name,
        top_category=top_category,
        category_path=category_path,
        brand=brand,
        price=price,
        thumbnail=thumbnail,
        url=url,
        text=text,
    )


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    # h in [0, 360)
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs(((h / 60) % 2) - 1))
    m = l - c / 2

    r1, g1, b1 = 0.0, 0.0, 0.0
    if 0 <= h < 60:
        r1, g1, b1 = c, x, 0
    elif 60 <= h < 120:
        r1, g1, b1 = x, c, 0
    elif 120 <= h < 180:
        r1, g1, b1 = 0, c, x
    elif 180 <= h < 240:
        r1, g1, b1 = 0, x, c
    elif 240 <= h < 300:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x

    r = int(round((r1 + m) * 255))
    g = int(round((g1 + m) * 255))
    b = int(round((b1 + m) * 255))
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def _color_for_category(name: str) -> tuple[int, int, int, int]:
    # Deterministic, reasonably distinct. Hash to hue.
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) % 360
    r, g, b = _hsl_to_rgb(float(h), 0.62, 0.52)
    return (r, g, b, 200)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Embed products into 2D and write index.html (deck.gl).")
    p.add_argument(
        "--products-dir",
        type=Path,
        default=Path("data/products"),
        help="Directory containing product JSON files (default: data/products)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("index.html"),
        help="Output HTML path (default: index.html)",
    )
    p.add_argument(
        "--model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="SentenceTransformers model name",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Embedding batch size (default: 64)",
    )
    p.add_argument(
        "--perplexity",
        type=float,
        default=40.0,
        help="t-SNE perplexity (default: 40)",
    )
    p.add_argument(
        "--max-iter",
        dest="max_iter",
        type=int,
        default=1500,
        help="t-SNE max iterations (default: 1500)",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    paths = sorted(args.products_dir.glob("*.json"), key=lambda p: p.name)
    if not paths:
        raise SystemExit(f"no product json files found in {args.products_dir}")

    records: list[ProductRecord] = []
    for path in paths:
        prod = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(prod, dict):
            continue
        records.append(_product_to_record(prod))

    texts = [r.text for r in records]

    model = SentenceTransformer(args.model)
    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    emb = np.asarray(embeddings, dtype=np.float32)

    coords = TSNE(
        n_components=2,
        perplexity=args.perplexity,
        learning_rate="auto",
        init="random",
        random_state=args.seed,
        early_exaggeration=18.0,
        angle=0.5,
        max_iter=args.max_iter,
        metric="cosine",
    ).fit_transform(emb)

    # Build category palette + counts.
    cat_counts: dict[str, int] = {}
    for r in records:
        cat_counts[r.top_category] = cat_counts.get(r.top_category, 0) + 1

    categories = [
        {
            "name": name,
            "count": count,
            "color": list(_color_for_category(name)[:3]),
        }
        for name, count in sorted(cat_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    cat_to_color = {c["name"]: _color_for_category(c["name"]) for c in categories}

    points = []
    for r, (x, y) in zip(records, coords, strict=True):
        color = cat_to_color.get(r.top_category, (90, 90, 90, 200))
        points.append(
            {
                "id": r.id,
                "name": r.name,
                "top_category": r.top_category,
                "category_path": r.category_path,
                "price": r.price,
                "thumbnail": r.thumbnail,
                "url": r.url,
                "x": float(x),
                "y": float(y),
                "color": list(color),
            }
        )

    points_json = json.dumps(points, ensure_ascii=False, separators=(",", ":"))
    categories_json = json.dumps(categories, ensure_ascii=False, separators=(",", ":"))

    html = (
        HTML_TEMPLATE.replace("__POINTS_JSON__", points_json)
        .replace("__CATEGORIES_JSON__", categories_json)
    )
    args.out.write_text(html, encoding="utf-8")
    print(f"wrote {args.out} ({len(points)} points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
