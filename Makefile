.PHONY: data index upload clean help

help:
	@echo "Targets:"
	@echo "  data   - Download Mercadona catalog JSON into data/"
	@echo "  index  - Build index.html from data/products"
	@echo "  upload - Upload data/ to Hugging Face dataset datania/mercadona-catalog"
	@echo "  clean  - Remove data/"

.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

data: .uv
	uv run mercadona.py

index: .uv
	uv run --script embed_products.py --products-dir data/products --out index.html

upload:
	uvx --from "huggingface_hub[hf_xet]" hf upload-large-folder \
		--token=${HUGGINGFACE_TOKEN} \
		--repo-type dataset \
		--num-workers 4 \
		datania/mercadona-catalog data/

clean:
	rm -rf data/
