# 🍍 mercadona-catalog

Descarga el catálogo (JSON) de la [API pública](api.md) de la tienda online de Mercadona y lo sube a [Hugging Face](https://huggingface.co/datasets/datania/mercadona-catalog).

## Uso

```bash
make data      # descargar catálogo a data/
make upload    # subir a Hugging Face
make clean     # limpiar data/
```

La subida usa `hf upload` con la versión fijada en `pyproject.toml` y `uv.lock`.
El contenido de `data/` se sube a la raíz del dataset. La CLI divide las carpetas
grandes en varios commits y permite reanudar una subida interrumpida.
`make upload-check` comprueba que la CLI está disponible sin subir datos ni usar
credenciales; GitHub Actions lo ejecuta antes de descargar el catálogo.

El script acepta opciones (`uv run mercadona.py --help`): concurrencia, delay, filtro por categoría, límite de productos, etc.

Por defecto descarga con un solo worker y pausas de 2 segundos entre requests (`--concurrency 1 --delay 2`). Un catálogo completo puede tardar unas 3 horas.

## Requisitos

- [`uv`](https://docs.astral.sh/uv/)
- `HUGGINGFACE_TOKEN` (para `make upload`)
