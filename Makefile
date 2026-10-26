.PHONY: data index upload upload-check clean help

help:
	@echo "Targets:"
	@echo "  data   - Download Mercadona catalog JSON into data/"
	@echo "  index  - Build index.html from data/products"
	@echo "  upload - Upload data/ to Hugging Face dataset datania/mercadona-catalog"
	@echo "  upload-check - Check the locked Hugging Face upload CLI without uploading"
	@echo "  clean  - Remove data/"

.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

data: .uv
	uv run mercadona.py

index: .uv
	uv run --script embed_products.py --products-dir data/products --out index.html

upload-check: .uv
	uv run --locked --group upload hf upload --help > /dev/null

upload: .uv
	HF_TOKEN="$${HUGGINGFACE_TOKEN}" uv run --locked --group upload hf upload \
		--repo-type dataset \
		datania/mercadona-catalog data/ .

clean:
	rm -rf data/
