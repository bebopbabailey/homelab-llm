# NOW

Active
- Add a durable `task-youtube-summary` LiteLLM lane that accepts a YouTube URL,
  fetches captions through `youtube-transcript-api`, returns a comprehensive
  summary, and supports follow-up Q&A through the existing Responses-first
  gateway contract.

NEXT UP
- After the lane lands, decide whether long-video follow-up should stay
  synthesis-grounded or gain a separate durable transcript storage path.
