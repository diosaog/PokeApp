from __future__ import annotations


def coins_from_badges(sav_json: dict) -> int:
    """Count badges (max 8) and return coins: 4 per badge."""
    def scan(o) -> int:
        tot = 0
        if isinstance(o, dict):
            for k, v in o.items():
                kl = str(k).lower()
                if "badge" in kl:
                    try:
                        if bool(v):
                            tot += 1
                    except Exception:
                        pass
                tot += scan(v)
        elif isinstance(o, (list, tuple)):
            for it in o:
                tot += scan(it)
        return tot

    badges = min(scan(sav_json), 8)
    return badges * 4
