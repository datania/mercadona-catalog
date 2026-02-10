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

# Mercadona catalog

Catálogo de productos y precios de la tienda online de Mercadona, exportado desde su API pública (no oficial) y publicado por Datania.

## Contenido

- `categories.json`: árbol de categorías
- `categories/*.json`: detalle por categoría
- `product_ids.json`: índice de ids de producto
- `products/*.json`: detalle completo por producto (incluye precio y metadatos)

## Notas

- API no oficial. Puede cambiar sin aviso.
- Respeta rate limits.
