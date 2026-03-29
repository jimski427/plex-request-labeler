# Plex Request Labeler

Automatically tags the requester's username as a **Plex Label** on the matching media item every time a request is made or approved in Overseerr.

## How it Works

1. Overseerr sends a webhook to this server when a request is created or approved.
2. The server extracts the requester's username and the media's TMDB/TVDB ID.
3. It searches **all Plex library sections** for the media item.
4. It adds the username (e.g. `jimski427`) as a **Plex Label** on the item.

---

## Setup

### 1. Get your Plex Token

Follow the official guide:  
https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
PLEX_URL=http://192.168.1.100:32400
PLEX_TOKEN=your_plex_token_here
WEBHOOK_PORT=5000
```

### 3. Configure Overseerr Webhook

In Overseerr, go to **Settings → Notifications → Webhook** and add a new webhook:

- **Webhook URL:** `http://<your-server-ip>:5000/webhook`
- **Notification Types:** Enable at minimum:
  - `Request Pending Approval`
  - `Request Approved`
  - `Media Available`

---

## Running

### With Python directly

```bash
pip install -r requirements.txt
python app.py
```

### With Docker

```bash
docker build -t plex-request-labeler .
docker run -d --env-file .env -p 5000:5000 plex-request-labeler
```

### With Docker Compose

```bash
docker compose up -d
```

---

## Notes

- Labels are **only the username** (e.g. `jimski427`) — no prefixes.
- If the label already exists on the item it will not be added twice.
- If the media is not yet in Plex when the webhook fires, a warning is logged and the webhook returns `200 OK` (Overseerr will not retry).
- All Plex library sections are searched automatically — no need to specify library names.
