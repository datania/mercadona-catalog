# 🍍 mercadona-catalog

Descarga el catálogo (JSON) de la [API pública](api.md) de la tienda online de Mercadona y lo sube a [Hugging Face](https://huggingface.co/datasets/datania/mercadona-catalog).

## Uso

```bash
make data      # descargar catálogo a data/
make upload    # subir a Hugging Face
make clean     # limpiar data/
```

El script acepta opciones (`uv run mercadona.py --help`): concurrencia, delay, filtro por categoría, límite de productos, etc.

## Requisitos

- [`uv`](https://docs.astral.sh/uv/)
- `HUGGINGFACE_TOKEN` (para `make upload`)
