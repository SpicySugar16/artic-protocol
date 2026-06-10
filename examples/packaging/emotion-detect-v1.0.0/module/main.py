"""
emotion-detect: Artic Protocol module example

Reads text from stdin as Artic message envelopes,
detects emotions, writes results back to stdout.

Install:
  engine install emotion-detect-v1.0.0.amod

Run:
  echo '{"id":"...","kind":"request","to":"emotion.detect","payload":{"text":"I am so happy!"}}' \\
    | python module/main.py
"""

import json
import os
import sys

# ── Emotion keyword sets ──────────────────────────────
EMOTION_KEYWORDS = {
    "joy":       ["happy", "glad", "wonderful", "great", "love", "amazing", "excellent", "😊", "🎉"],
    "sadness":   ["sad", "unhappy", "sorry", "miss", "cry", "depressed", "😢", "💔"],
    "anger":     ["angry", "furious", "annoyed", "hate", "terrible", "😠", "🤬"],
    "fear":      ["scared", "afraid", "worried", "nervous", "terrified", "😨", "😰"],
    "surprise":  ["wow", "surprise", "unexpected", "shock", "incredible", "😲", "🤯"],
    "disgust":   ["disgusting", "gross", "awful", "horrible", "🤢", "🤮"],
}


def detect_emotion(text: str) -> dict:
    """Simple keyword-based emotion detection."""
    text_lower = text.lower()
    scores = {emotion: 0.0 for emotion in EMOTION_KEYWORDS}
    total = 0

    for emotion, keywords in EMOTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[emotion] += 1.0
                total += 1

    if total == 0:
        return {"primary": "neutral", "scores": scores, "confidence": 0.0}

    # Normalise scores to 0-1
    for emotion in scores:
        scores[emotion] = round(scores[emotion] / total, 3)

    primary = max(scores, key=scores.get)
    confidence = round(scores[primary], 3)

    return {"primary": primary, "scores": scores, "confidence": confidence}


def main():
    """Main loop: read envelopes from stdin, write responses to stdout."""
    coupling_addr = os.environ.get("ARTIC_COUPLING", "stdin/stdout")
    module_id = os.environ.get("ARTIC_MODULE_ID", "emotion.detect")

    log = lambda msg: print(f"[{module_id}] {msg}", file=sys.stderr)

    log(f"Starting on {coupling_addr}")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            envelope = json.loads(line)
        except json.JSONDecodeError as e:
            log(f"Invalid JSON: {e}")
            continue

        if envelope.get("kind") != "request":
            continue

        payload = envelope.get("payload", {})
        text = payload.get("text", "")

        log(f"Detecting emotion in: {text[:40]}...")

        result = detect_emotion(text)

        response = {
            "id": envelope["id"],
            "from": module_id,
            "to": envelope.get("from", "engine"),
            "kind": "response",
            "payload": result,
            "reply_to": envelope["id"],
            "timestamp": envelope.get("timestamp", 0),
        }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
