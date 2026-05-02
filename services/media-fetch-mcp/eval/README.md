# `media-fetch-mcp` Eval Notes

This directory is the service-local home for lightweight regression coverage of
`media-fetch-mcp`.

It is intentionally simple in the first pass:
- human-readable starter cases
- JSONL query packs kept close to the service
- no dedicated eval runner yet

## What Belongs Here

Put these kinds of artifacts in this directory:
- query packs for direct MCP tool checks
- sample/manual acceptance cases
- future stable fixtures for mocked extraction/search payloads

Do not put:
- platform-wide evals shared across unrelated services
- bulky one-off debug dumps
- service runtime logs

## Current Starter Pack

- [query_pack.web.v1.jsonl](./query_pack.web.v1.jsonl)

That file is the initial “what should still work?” pack for:
- search normalization
- fetch/extraction success
- quick-mode happy path
- research-mode session build path
- an expected upstream failure case

## How To Add A Case

Add one JSON object per line with:
- `case_id`
- `tool`
- `kind`
- `input`
- `expect`
- optional `notes`

Prefer cases that answer one of these:
- does the tool succeed on a stable target?
- does it fail with the expected error class?
- does the output shape still include the fields callers rely on?
- does a known caveat stay documented instead of regressing silently?

## How To Use The Pack

For now, use the pack as a manual/semiautomated checklist:
1. pick a case
2. call the tool directly over MCP
3. compare the result to the `expect` notes
4. update the pack when the contract intentionally changes

If this service grows a dedicated eval runner later, this directory is the
intended place for that runner to consume packs from.
