from __future__ import annotations


def _bitcount(n: int) -> int:
    try:
        return int(bin(int(n)).count("1"))
    except Exception:
        return 0


def _sum_truthy(iterable) -> int:
    return sum(1 for x in iterable if bool(x))


def _count_badges_from_value(v) -> int:
    if isinstance(v, (list, tuple)):
        return _sum_truthy(v)
    if isinstance(v, dict):
        return _sum_truthy(v.values())
    if isinstance(v, int):
        return _bitcount(v)
    if isinstance(v, bool):
        return 1 if v else 0
    return 0


def count_badges(sav_json: dict) -> int:
    if not isinstance(sav_json, dict):
        return 0
    for path in [("trainer", "badges"), ("Trainer", "Badges"), ("badges",), ("Badges",)]:
        cur, ok = sav_json, True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok:
            cnt = _count_badges_from_value(cur)
            if cnt:
                return min(cnt, 8)
    for k in ("BadgeFlags", "Badges", "badgesFlags", "badge_flags"):
        if k in sav_json and isinstance(sav_json[k], int):
            return min(_bitcount(sav_json[k]), 8)

    sinnoh = {"coal", "forest", "relic", "cobble", "fen", "mine", "icicle", "beacon"}
    seen_keys: set[str] = set()
    total = 0

    def scan(o):
        nonlocal total
        if isinstance(o, dict):
            for kk, vv in o.items():
                kl = str(kk).lower()
                if "badge" in kl:
                    total += _count_badges_from_value(vv)
                    continue
                for nm in sinnoh:
                    if nm in kl:
                        if nm not in seen_keys:
                            seen_keys.add(nm)
                            c = _count_badges_from_value(vv)
                            total += c if c else 1
                        continue
                scan(vv)
        elif isinstance(o, (list, tuple)):
            for it in o:
                scan(it)

    scan(sav_json)
    return min(total, 8)
