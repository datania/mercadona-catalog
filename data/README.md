---
license: mit
configs:
  - config_name: default
    data_files:
      - split: catalog
        path:
          - categories.json
          - product_ids.json
          - categories/*.json
          - products/*.json
    default: true
---

# 🍍 Mercadona Catalog

Catálogo completo de productos y precios de la tienda online de [Mercadona](https://tienda.mercadona.es), exportado semanalmente desde su API pública (no oficial).

## Estructura

| Archivo | Contenido |
|---|---|
| `categories.json` | Árbol de categorías (secciones y subcategorías) |
| `categories/<id>.json` | Detalle por categoría con productos asociados |
| `product_ids.json` | Índice con todos los IDs de producto |
| `products/<id>.json` | Detalle completo por producto (precio, descripción, imágenes, ...) |

## Notas

- API no oficial. Puede cambiar sin aviso.
- Actualización semanal (lunes) via [GitHub Actions](https://github.com/datania/mercadona-catalog).
- Respeta rate limits.
