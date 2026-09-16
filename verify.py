#!/usr/bin/env python3
"""Work through the hand-check queue and write the answers in.

    python3 verify.py list [N]          show the next N addresses to check
    python3 verify.py add < batch.json  write a batch of checked addresses
    python3 verify.py stats             how far along we are

A batch is a JSON list, one object per address:

    [{"key": "hofstraat||paramaribo",
      "lat": 5.8261, "lon": -55.1584,
      "label": "Hofstraat, Centrum, Paramaribo",
      "confidence": "street",          // exact | street | area | none
      "radius_m": 0,                   // only for "area"
      "method": "Google Maps (handmatig)",
      "note": ""}]

Keys come straight from the queue, so nothing has to be typed twice. An address
written here is never queued again - that is the whole point.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perceel import verified


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    q = json.loads(verified.QUEUE.read_text(encoding="utf-8")) if verified.QUEUE.exists() else {"items": []}

    if cmd == "list":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 25
        print(json.dumps(q["items"][:n], ensure_ascii=False, indent=1))
    elif cmd == "add":
        rows = json.load(sys.stdin)
        added = verified.merge(rows)
        print(f"{added} new, {len(verified.load()['entries'])} verified in total")
    elif cmd == "stats":
        print(f"verified : {len(verified.load()['entries'])}")
        print(f"queue    : {len(q.get('items', []))}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
