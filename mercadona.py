import argparse
import asyncio
import json
import os
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

import httpx

API_BASE_URL = "https://tienda.mercadona.es/api"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "es-ES,es;q=0.9",
}


@dataclass(frozen=True)
class FetchResult:
    url: str
    path: Path
    status_code: int
    wrote: bool


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Caché local de la API pública de Mercadona. Descarga JSON y lo guarda en disco "
            "con rutas tipo categories.json, categories/112.json, products/65235.json."
        )
    )
    p.add_argument(
        "--out",
        type=Path,
        default=Path("data"),
        help="Directorio de salida (default: data)",
    )
    p.add_argument(
        "--base-url",
        default=API_BASE_URL,
        help=f"Base URL API (default: {API_BASE_URL})",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Concurrencia para descargas de products/{id} (default: 1)",
    )
    p.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay entre requests por worker, segundos (default: 2)",
    )
    p.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Reintentos por request (default: 3)",
    )
    p.add_argument(
        "--skip-unchanged",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="No reescribir JSON si el contenido no cambia (default: true)",
    )
    p.add_argument(
        "--max-products",
        type=int,
        default=0,
        help="Limitar número de productos a descargar (0 sin límite)",
    )
    p.add_argument(
        "--only-category-ids",
        type=str,
        default="",
        help="CSV de category ids (2º nivel) a procesar (ej: 112,156)",
    )
    args = p.parse_args()
    if args.concurrency < 1 or args.retries < 1 or not 0 <= args.delay < float("inf"):
        p.error("concurrency y retries deben ser >= 1; delay debe ser finito y >= 0")
    return args


def _api_rel_to_out_path(api_rel: str) -> Path:
    api_rel = api_rel.lstrip("/")
    if api_rel.endswith("/"):
        name = api_rel.removesuffix("/")
        return Path(f"{name}.json")

    parts = [p for p in api_rel.split("/") if p]
    if not parts:
        raise ValueError("empty api_rel")

    if len(parts) == 1:
        return Path(f"{parts[0]}.json")

    *dirs, leaf = parts
    return Path(*dirs) / f"{leaf}.json"


def _json_dumps_stable(data: object) -> str:
    return (
        json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _write_json(path: Path, data: object, *, skip_unchanged: bool) -> bool:
    content = _json_dumps_stable(data)

    if skip_unchanged and path.exists():
        old = path.read_text(encoding="utf-8")
        if old == content:
            return False

    _atomic_write_text(path, content)
    return True


def _retry_backoff_seconds(attempt: int) -> float:
    return min(60.0, 2.0 * (2 ** (attempt - 1)))


def _validate_payload(data: object, url: str) -> None:
    if not isinstance(data, dict):
        raise TypeError(f"expected a JSON object: {url}")
    if "code" in data or "_error" in data:
        message = data.get("en_message") or data.get("_error") or data.get("code")
        raise ValueError(f"API error for {url}: {message}")

    parts = httpx.URL(url).path.rstrip("/").split("/")
    if parts[-1] == "categories":
        valid = isinstance(data.get("results"), list) and bool(data["results"])
    else:
        valid = str(data.get("id")) == parts[-1]
        if parts[-2] == "products":
            valid = valid and bool(data.get("display_name"))
        else:
            valid = valid and isinstance(data.get("categories"), list)
    if not valid:
        raise ValueError(f"invalid catalog payload: {url}")


async def _fetch_json(
    client: httpx.AsyncClient,
    url: str,
    out_path: Path,
    *,
    retries: int,
    skip_unchanged: bool,
) -> FetchResult:
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            resp = await client.get(url)
        except httpx.TransportError as e:
            last_exc = e
            if attempt < retries:
                await asyncio.sleep(_retry_backoff_seconds(attempt))
                continue
            raise RuntimeError(
                f"request failed after {retries} attempts: {url}"
            ) from last_exc

        status = resp.status_code
        if status >= 500 and attempt < retries:
            await asyncio.sleep(_retry_backoff_seconds(attempt))
            continue
        # Do not retry blocking responses (including HTTP 200 API errors).
        resp.raise_for_status()
        data = resp.json()
        _validate_payload(data, url)
        wrote = _write_json(out_path, data, skip_unchanged=skip_unchanged)
        return FetchResult(
            url=url,
            path=out_path,
            status_code=status,
            wrote=wrote,
        )

    raise AssertionError("unreachable")


def _iter_second_level_category_ids(categories_root: dict) -> list[int]:
    results = categories_root.get("results")
    if not isinstance(results, list):
        raise TypeError("unexpected categories root payload. Missing 'results'.")

    ids: list[int] = []
    for top in results:
        cats = top.get("categories")
        if not isinstance(cats, list):
            continue
        for c in cats:
            cid = c.get("id")
            if isinstance(cid, int):
                ids.append(cid)
    return ids


def _collect_product_ids_from_category_payload(payload: object) -> set[str]:
    product_ids: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            products = node.get("products")
            if isinstance(products, list):
                for p in products:
                    if not isinstance(p, dict):
                        continue
                    pid = p.get("id")
                    if isinstance(pid, str) and pid:
                        product_ids.add(pid)

            for k, v in node.items():
                if k == "products":
                    continue
                walk(v)
            return

        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return product_ids


async def _bounded_gather[T, R](
    limit: int, items: Iterable[T], fetch: Callable[[T], Awaitable[R]]
) -> list[R]:
    pending = iter(items)
    results: list[R] = []

    async def worker() -> None:
        for item in pending:
            results.append(await fetch(item))

    async with asyncio.TaskGroup() as group:
        for _ in range(limit):
            group.create_task(worker())
    return results


def _format_fetch_result(res: FetchResult, out_dir: Path) -> str:
    base = f"[{res.status_code}] {res.path.relative_to(out_dir)}"
    if not res.wrote:
        return f"{base} (unchanged)"
    return base


async def main() -> int:
    args = _parse_args()
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    only_category_ids: set[int] = set()
    if args.only_category_ids.strip():
        only_category_ids = {
            int(x.strip()) for x in args.only_category_ids.split(",") if x.strip()
        }

    timeout = httpx.Timeout(20.0, connect=20.0)
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=40)

    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS,
        timeout=timeout,
        limits=limits,
        follow_redirects=True,
    ) as client:
        categories_url = f"{args.base_url}/categories/"
        categories_out = out_dir / _api_rel_to_out_path("categories/")
        res = await _fetch_json(
            client,
            categories_url,
            categories_out,
            retries=args.retries,
            skip_unchanged=args.skip_unchanged,
        )
        print(_format_fetch_result(res, out_dir))

        categories_root = json.loads(categories_out.read_text(encoding="utf-8"))
        cat_ids = _iter_second_level_category_ids(categories_root)
        if only_category_ids:
            cat_ids = [cid for cid in cat_ids if cid in only_category_ids]

        all_product_ids: set[str] = set()

        for cid in cat_ids:
            await asyncio.sleep(args.delay)
            url = f"{args.base_url}/categories/{cid}"
            out_path = out_dir / _api_rel_to_out_path(f"categories/{cid}")
            res = await _fetch_json(
                client,
                url,
                out_path,
                retries=args.retries,
                skip_unchanged=args.skip_unchanged,
            )
            print(_format_fetch_result(res, out_dir))

            payload = json.loads(out_path.read_text(encoding="utf-8"))
            all_product_ids |= _collect_product_ids_from_category_payload(payload)

        product_ids = sorted(all_product_ids)
        if args.max_products and args.max_products > 0:
            product_ids = product_ids[: args.max_products]

        if not product_ids:
            raise ValueError("no products found; refusing to publish an empty catalog")

        completed = 0

        async def fetch_one(pid: str) -> FetchResult:
            nonlocal completed
            await asyncio.sleep(args.delay)
            url = f"{args.base_url}/products/{pid}"
            out_path = out_dir / _api_rel_to_out_path(f"products/{pid}")
            r = await _fetch_json(
                client,
                url,
                out_path,
                retries=args.retries,
                skip_unchanged=args.skip_unchanged,
            )
            completed += 1
            if completed % 25 == 0 or completed == len(product_ids):
                print(f"products fetched: {completed}/{len(product_ids)}", flush=True)
            return r

        results = await _bounded_gather(args.concurrency, product_ids, fetch_one)

        wrote = sum(1 for r in results if r.wrote)
        _write_json(
            out_dir / "product_ids.json",
            {"count": len(product_ids), "product_ids": product_ids},
            skip_unchanged=args.skip_unchanged,
        )
        print(f"products fetched: {len(results)}, wrote: {wrote}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
