# youtube-transcript-api

Localhost-only OpenAI-compatible YouTube transcript acquisition service.

Use it through LiteLLM:

```json
{
  "model": "task-youtube-transcript",
  "messages": [
    {"role": "user", "content": "https://youtu.be/dQw4w9WgXcQ"}
  ]
}
```

The assistant message content is plain timestamped transcript text.
