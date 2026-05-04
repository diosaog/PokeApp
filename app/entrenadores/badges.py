from __future__ import annotations

import unicodedata


MAX_BADGES = 8

UNOVA_BW2_BADGE_NAMES = (
    "Base",
    "Ponzo\u00f1a",
    "\u00c9litro",
    "Voltio",
    "Temblor",
    "Jet",
    "Leyenda",
    "Ola",
)

UNOVA_BW2_BADGE_KEYWORDS = (
    ("base", "basic", "cheren", "aspertia"),
    ("ponzo", "ponzona", "poison", "toxic", "toxica", "roxie", "homika", "virbank"),
    ("litro", "elitro", "insect", "beetle", "bug", "burgh", "castelia"),
    ("voltio", "bolt", "electric", "elesa", "nimbasa"),
    ("temblor", "quake", "ground", "clay", "driftveil"),
    ("jet", "flying", "skyla", "mistralton"),
    ("leyenda", "legend", "dragon", "drayden", "lirio", "opalucid"),
    ("ola", "wave", "water", "marlon", "humilau"),
)


def _bitcount(n: int) -> int:
    try:
        return int(bin(int(n)).count("1"))
    except Exception:
        return 0


def _clamp_badges(n: int) -> int:
    try:
        return max(0, min(int(n), MAX_BADGES))
    except Exception:
        return 0


def _norm(s: object) -> str:
    text = unicodedata.normalize("NFKD", str(s).lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _sum_truthy(iterable) -> int:
    return sum(1 for x in iterable if bool(x))


def _count_badges_from_value(v, *, numeric_as_count: bool = False) -> int:
    if isinstance(v, (list, tuple)):
        return _clamp_badges(_sum_truthy(v))
    if isinstance(v, dict):
        return _clamp_badges(_sum_truthy(v.values()))
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, int):
        return _clamp_badges(v if numeric_as_count else _bitcount(v))
    if isinstance(v, str):
        s = v.strip()
        if s.isdigit():
            raw = int(s)
            return _clamp_badges(raw if numeric_as_count else _bitcount(raw))
    return 0


def _get_path(data: dict, path: tuple[str, ...]):
    cur = data
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None, False
    return cur, True


def count_badges(sav_json: dict) -> int:
    if not isinstance(sav_json, dict):
        return 0

    count_paths = [
        ("Trainer", "BadgeCount"),
        ("trainer", "badge_count"),
        ("BadgeCount",),
        ("badge_count",),
        ("badges_count",),
    ]
    for path in count_paths:
        cur, ok = _get_path(sav_json, path)
        if ok:
            cnt = _count_badges_from_value(cur, numeric_as_count=True)
            if cnt:
                return cnt

    flag_paths = [
        ("Trainer", "BadgeFlags"),
        ("Trainer", "Badges"),
        ("Trainer", "Badges16"),
        ("trainer", "badge_flags"),
        ("trainer", "badges"),
        ("BadgeFlags",),
        ("Badges",),
        ("Badges16",),
        ("badgesFlags",),
        ("badge_flags",),
        ("badges",),
    ]
    for path in flag_paths:
        cur, ok = _get_path(sav_json, path)
        if ok:
            cnt = _count_badges_from_value(cur)
            if cnt:
                return cnt

    for k in ("BadgeFlags", "Badges", "Badges16", "badgesFlags", "badge_flags"):
        if k in sav_json and isinstance(sav_json[k], int):
            return _clamp_badges(_bitcount(sav_json[k]))

    seen_keys: set[str] = set()
    total = 0

    def scan(o):
        nonlocal total
        if isinstance(o, dict):
            for kk, vv in o.items():
                kl = _norm(kk)
                if "badgecount" in kl or "badge_count" in kl:
                    total += _count_badges_from_value(vv, numeric_as_count=True)
                    continue
                if "badge" in kl:
                    total += _count_badges_from_value(vv)
                    continue
                for idx, names in enumerate(UNOVA_BW2_BADGE_KEYWORDS):
                    if any(nm in kl for nm in names):
                        marker = str(idx)
                        if marker not in seen_keys:
                            seen_keys.add(marker)
                            c = _count_badges_from_value(vv)
                            total += c if c else 1
                        continue
                scan(vv)
        elif isinstance(o, (list, tuple)):
            for it in o:
                scan(it)

    scan(sav_json)
    return _clamp_badges(total)
