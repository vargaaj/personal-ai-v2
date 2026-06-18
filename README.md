# Loop Review Console

A local NiceGUI/FastAPI app for reviewing and editing the latest JSON files produced by AnythingLLM loops.

For the local AnythingLLM Docker and scheduled-job setup, see
[README_ANYTHINGLLM_LOCAL.md](README_ANYTHINGLLM_LOCAL.md).

## Setup

```powershell
conda create -n personal-ai python=3.12 pip
conda activate personal-ai
python -m pip install -r requirements.txt
```

If `personal-ai` already exists but does not have its own Python:

```powershell
conda install -n personal-ai python=3.12 pip
```

## Run

```powershell
conda activate personal-ai
python -m loop_review.main
```

Open <http://127.0.0.1:8080>.

## File Contract

By default the app reads and writes JSON files:

```text
data/loops/gmail_state.json
data/loops/finance.json
data/loops/home.json
data/loops/health.json
data/loops/food.json
data/loops/ai_news.json
```

Set `LOOPS_DIR` to point at another folder. The app expects one JSON file per loop and rewrites those files directly when saving or toggling items.

Generic loop files use this shape:

```json
{
  "id": "home",
  "title": "Home",
  "last_updated": "2026-06-11",
  "sections": [
    {
      "title": "Maintenance",
      "items": [
        {
          "id": "replace-hvac-filter",
          "text": "Replace HVAC filter.",
          "checked": false,
          "details": "",
          "link": null
        }
      ]
    }
  ]
}
```

The Gmail loop can also use the simpler daily-agent state shape:

```json
{
  "last_updated": "2026-06-11",
  "emails": [
    {
      "message_id": "message-id",
      "sender": "Sender",
      "subject": "Subject",
      "date": "2026-06-11",
      "summary": "Short useful summary.",
      "section": "needs_attention",
      "status": "open"
    }
  ]
}
```

## API

- `GET /api/loops`
- `GET /api/loops/{loop}`
- `PUT /api/loops/{loop}`
- `POST /api/loops/{loop}/items`
- `PATCH /api/loops/{loop}/items/{item_id}`

The app rejects saves and item toggles with HTTP `409` if a file has changed on disk since the caller loaded it.

Create manual items with:

```json
{
  "section": "Maintenance",
  "text": "Clean dryer vent",
  "details": "Before weekend",
  "link": ""
}
```

AI news items should use the generic loop shape with source metadata:

```json
{
  "id": "stable-news-id",
  "text": "Article, post, or video title",
  "checked": false,
  "details": "Short summary of why this matters.",
  "link": "https://example.com/source",
  "source": "Publication, account, channel, or author",
  "source_type": "article | x_post | youtube",
  "published_date": "2026-06-11"
}
```
