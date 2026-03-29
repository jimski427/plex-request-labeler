import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from plexapi.server import PlexServer

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PLEX_URL = os.getenv("PLEX_URL")
PLEX_TOKEN = os.getenv("PLEX_TOKEN")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))

# Notification types that indicate a request has been made or approved
HANDLED_NOTIFICATION_TYPES = {
    "MEDIA_AVAILABLE",
    "REQUEST_APPROVED",
    "REQUEST_PENDING_APPROVAL",
}


def get_plex_server():
    if not PLEX_URL or not PLEX_TOKEN:
        raise RuntimeError("PLEX_URL and PLEX_TOKEN must be set in environment.")
    return PlexServer(PLEX_URL, PLEX_TOKEN)


def add_label_to_media(plex: PlexServer, media_type: str, tmdb_id: str, tvdb_id: str, username: str) -> bool:
    """Search all Plex library sections for the media item and add the username label."""
    guids_to_try = []
    if tmdb_id:
        guids_to_try.append(f"tmdb://{tmdb_id}")
    if tvdb_id:
        guids_to_try.append(f"tvdb://{tvdb_id}")

    if not guids_to_try:
        logger.warning("No TMDB or TVDB ID provided — cannot locate media in Plex.")
        return False

    for section in plex.library.sections():
        # Filter to matching section type
        if media_type == "movie" and section.type != "movie":
            continue
        if media_type == "tv" and section.type != "show":
            continue

        for guid in guids_to_try:
            try:
                results = section.search(guid=guid)
                if not results:
                    continue

                for item in results:
                    existing_labels = [label.tag for label in item.labels]
                    if username in existing_labels:
                        logger.info(
                            "Label '%s' already exists on '%s' — skipping.", username, item.title
                        )
                    else:
                        item.addLabel(username)
                        logger.info(
                            "Added label '%s' to '%s' in library '%s'.",
                            username,
                            item.title,
                            section.title,
                        )
                return True
            except Exception as exc:
                logger.debug(
                    "Could not find %s in section '%s': %s", guid, section.title, exc
                )

    logger.warning(
        "Media not found in any Plex library (tmdb_id=%s, tvdb_id=%s, type=%s).",
        tmdb_id,
        tvdb_id,
        media_type,
    )
    return False


@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.get_json(silent=True)
    if not payload:
        logger.warning("Received empty or non-JSON payload.")
        return jsonify({"status": "ignored", "reason": "no payload"}), 200

    notification_type = payload.get("notification_type", "")
    if notification_type not in HANDLED_NOTIFICATION_TYPES:
        logger.info("Ignoring notification type: %s", notification_type)
        return jsonify({"status": "ignored", "reason": "unhandled notification type"}), 200

    media = payload.get("media", {})
    media_type = media.get("mediaType", "")
    tmdb_id = str(media.get("tmdbId") or "").strip()
    tvdb_id = str(media.get("tvdbId") or "").strip()

    request_info = payload.get("request", {})
    requested_by = request_info.get("requestedBy", {})
    username = (requested_by.get("username") or "").strip()

    if not username:
        logger.warning("No username found in webhook payload — skipping.")
        return jsonify({"status": "ignored", "reason": "no username"}), 200

    if media_type not in ("movie", "tv"):
        logger.warning("Unknown media type '%s' — skipping.", media_type)
        return jsonify({"status": "ignored", "reason": "unknown media type"}), 200

    try:
        plex = get_plex_server()
        add_label_to_media(plex, media_type, tmdb_id, tvdb_id, username)
    except Exception as exc:
        logger.error("Error while processing webhook: %s", exc)

    # Always return 200 to prevent Overseerr from retrying
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    logger.info("Starting Plex Request Labeler on port %d", WEBHOOK_PORT)
    app.run(host="0.0.0.0", port=WEBHOOK_PORT)
