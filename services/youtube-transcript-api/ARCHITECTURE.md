# Architecture: youtube-transcript-api

`youtube-transcript-api` is a narrow acquisition primitive:

```text
client
-> LiteLLM model=task-youtube-transcript
-> youtube-transcript-api
-> YouTube caption transcript
-> plain timed transcript text
```

The service intentionally does not own summarization, document ingestion,
retrieval, transcript cleanup, ASR fallback, or translation. Downstream services
can consume the canonical transcript object when they need structured timed
text.
