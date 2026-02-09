# Data Registries

## Lexicon Registry
- File: `layer-data/registry/lexicon.jsonl`
- Purpose: deterministic term correction for known system/service names
  (e.g., LiteLLM, Open WebUI) without free-form rewriting.
- Intended use: apply only in *non-strict* transcript flows (e.g., clarify)
  or explicit post-processing steps. Do not use for verbatim modes.

### Schema (JSONL)
Each line is a single JSON object with these fields:
- `term_id` (string, kebab-case): stable identifier
- `canonical` (string): correct display form
- `aliases` (array of strings): acceptable variants from transcripts
- `aliases_norm` (array of strings): normalized forms of `aliases`
- `category` (string): e.g., `service`, `framework`, `network`
- `replace_policy` (string): `exact_phrase` or `word_boundary`
- `notes` (string, optional)
- `embedding_text` (string, optional): future vector store seed

### Normalization rule (for `aliases_norm`)
- lowercase
- remove spaces and punctuation
- keep ASCII letters/digits only

### Correction policy (minimal)
- Only replace when an alias matches exactly (after normalization).
- Do not infer new terms; do not expand scope beyond the registry.
- Log replacements when a pipeline uses the lexicon.
