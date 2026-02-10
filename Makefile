.PHONY: data upload clean help

help:
	@echo "Targets:"
	@echo "  data   - Download Mercadona catalog JSON into data/"
	@echo "  upload - Upload data/ to Hugging Face dataset datania/mercadona-catalog"
	@echo "  clean  - Remove data/"

.uv:
	@uv -V || echo 'Please install uv: https://docs.astral.sh/uv/getting-started/installation/'

data: .uv
	uv run mercadona.py

upload:
	uvx --from "huggingface_hub[hf_xet]" hf upload-large-folder \
		--token=${HUGGINGFACE_TOKEN} \
		--repo-type dataset \
		--num-workers 4 \
		datania/mercadona-catalog data/

clean:
	rm -rf data/
