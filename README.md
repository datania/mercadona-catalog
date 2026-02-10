# mercadona-catalog

Descarga el catálogo (JSON) expuesto por la API pública de la tienda online de Mercadona y lo sube a Hugging Face.

Los datos se guardan en `data/` y no se commitean en Git.

## Requisitos

- `uv`
- `HUGGINGFACE_TOKEN` para subir a Hugging Face

## Uso

Descargar:

```bash
make data
```

Subir a Hugging Face:

```bash
make upload
```

Dataset:

- `datania/mercadona-catalog`

## GitHub Actions

Workflow semanal. Ejecuta `make data` y luego `make upload`.

### Secrets

- `HUGGINGFACE_TOKEN`
