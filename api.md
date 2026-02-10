# Mercadona Tienda API (tienda.mercadona.es)

Documento no oficial. Endpoints observados en febrero 2026.

Objetivo:
- listar endpoints accesibles bajo `https://tienda.mercadona.es/api/`
- indicar métodos, parámetros, auth
- dar ejemplos `curl`

Notas:
- `https://tienda.mercadona.es/api` (raíz) responde 404.
- algunos recursos requieren slash final y devuelven 301 si falta (ejemplo `/api/home`).
- la API parece Django REST Framework (respuestas de `OPTIONS` con `name`, `renders`, `parses`, `actions`).
- robots.txt bloquea `/api` para crawlers. Respeta ToS.

## Parámetros comunes

Frecuentes en el frontend:
- `lang`: idioma (`es`, `en`, ...)
- `wh`: almacén (ejemplos vistos: `vlc1`, `mad1`, `bcn1`, `alc1`)

En muchos endpoints funcionan sin `lang` y sin `wh`.

## Headers observados

El frontend suele mandar:
- `x-version: v8451` (versión del frontend)
- `x-customer-device-id: <uuid>`
- `x-experiment-variants: ...` (a veces)

Para los endpoints de lectura probados no parecen obligatorios.

## Endpoints de catálogo (sin autenticación)

### Categorías

Lista de secciones y árbol de categorías.

- `GET /api/categories/` (200)
- `GET /api/categories/<id>/` (200)

Ejemplo:
```bash
curl 'https://tienda.mercadona.es/api/categories/'
curl 'https://tienda.mercadona.es/api/categories/112/'
```

Respuesta típica `/api/categories/`:
- `count`
- `results[]` con categorías y subcategorías

### Productos

Producto por id.

- `GET /api/products/<product_id>/` (200)
- `GET /api/products/<product_id>/similars/` (200)
- `GET /api/products/<product_id>/xselling/` (200)

Ejemplo:
```bash
curl 'https://tienda.mercadona.es/api/products/10005/'
curl 'https://tienda.mercadona.es/api/products/10005/similars/'
curl 'https://tienda.mercadona.es/api/products/10005/xselling/'
```

Notas:
- `/api/products/` (listado) da 404 (probado).
- `products/<id>/` y `xselling` suelen venir cacheados (`cache-control: public, max-age=1800`).

### Home (secciones del inicio)

- `GET /api/home/` (200)
- `GET /api/home/new-arrivals/` (200)
- `GET /api/home/price-drops/` (200)
- `GET /api/home/sections/<uuid>/` (200)

Ejemplo:
```bash
curl 'https://tienda.mercadona.es/api/home/' > home.json

# los UUID de secciones aparecen dentro de home.json como rutas /home/sections/<uuid>/
# ejemplo observado:
curl 'https://tienda.mercadona.es/api/home/sections/782e53ef-99f7-4cac-9912-ded6bbc0f004/'
```

## Endpoints relacionados con código postal (sin autenticación)

Sirven para fijar CP y derivar almacén (`wh`).

### Cambiar CP

- `PUT /api/postal-codes/actions/change-pc/` (200)
- `POST /api/postal-codes/actions/change-pc/` (también permitido según `Allow`, no verificado con payload)

Body JSON:
- `{"new_postal_code":"46001"}`

Ejemplo:
```bash
curl -X PUT \
  -H 'content-type: application/json' \
  --data '{"new_postal_code":"46001"}' \
  'https://tienda.mercadona.es/api/postal-codes/actions/change-pc/'
```

Headers de respuesta útiles (observados):
- `x-customer-pc: 46001`
- `x-customer-wh: vlc1`

### Validar / recuperar CP

- `GET /api/postal-codes/actions/retrieve-pc/<postal_code>/` (204)

Ejemplo:
```bash
curl -i 'https://tienda.mercadona.es/api/postal-codes/actions/retrieve-pc/46001/'
```

Nota:
- en el bundle JS aparece `/postal-codes/<pc>/next-available-delivery-day/` pero devolvió 404 en pruebas.

## Endpoints accesibles pero orientados a cuenta (requieren auth para operar)

Estos endpoints existen y suelen describirse con `OPTIONS`.

### Auth

- `POST /api/auth/tokens/` (login)

Inspección de schema:
```bash
curl -X OPTIONS 'https://tienda.mercadona.es/api/auth/tokens/'
```

### Customers (acciones)

- `POST /api/customers/actions/check-email/`
- `POST /api/customers/actions/recover-password/`
- `POST /api/customers/actions/change-password/`
- `POST /api/customers/actions/create_and_authenticate/` (en una prueba devolvió 500, endpoint no fiable)

Schema:
```bash
curl -X OPTIONS 'https://tienda.mercadona.es/api/customers/actions/check-email/'
```

### Carts

- `POST /api/carts/` (endpoint existe, `OPTIONS 200`)

Schema:
```bash
curl -X OPTIONS 'https://tienda.mercadona.es/api/carts/'
```

### Customers (recursos autenticados)

Ejemplo verificado:
- `GET /api/customers/<id>/cart/` responde 401 sin token.

En el bundle JS aparecen muchos más:
- `/customers/<id>/orders/...`
- `/customers/<id>/shopping-lists/...`
- `/customers/<id>/payment-cards/...`
- `/customers/<id>/addresses/...`

## Conversations (chat soporte)

Observado en el bundle JS:
- `GET /api/conversations/chats/setup/` (en prueba devolvió 400 por campos requeridos, endpoint existe)
- `POST /api/conversations/chats/<chat_id>/release/` (Allow: POST)
- `PUT /api/conversations/chats/<chat_id>/messages/<message_id>/media/`

## API versionada: /api/v1_1

Encontrado en código de terceros en GitHub y verificado con `curl`.

- `GET /api/v1_1/categories/` (200)
- `GET /api/v1_1/categories/<id>` (200)
- `GET /api/v1_1/products/<product_id>` (200)

Notas:
- `GET /api/v1_1/` devuelve 404.
- `GET /api/v1_1/products/` (listado) devuelve 404.

Ejemplo:
```bash
curl 'https://tienda.mercadona.es/api/v1_1/categories/'
curl 'https://tienda.mercadona.es/api/v1_1/products/10005'
```

## Cómo se obtuvieron estos endpoints

- inspección del bundle del frontend (`/v8451/index-*.js`)
- observación de tráfico en navegador al cambiar CP
- búsqueda en GitHub (código de terceros) para cadenas `tienda.mercadona.es/api`
- verificación manual con `curl` (códigos 2xx, 4xx)
