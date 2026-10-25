"""Owner-approved quick items (Rare Candy, Heart Scale) over the existing journal.

Owner decision (2026-10-26): free and unlimited for every trainer, within each
game's technical limits only; no coins, purchase, admin approval or economy
record. Public adding stays off until real Lime3DS certification enables the
prepared "add_item" switch. Count, hash and limits come from one snapshot, and
the native writer revalidates all of them before any change.
"""

from hashlib import sha256

from app.launcher.write_engine import WriteIntent
from app.launcher.write_files import WriteSafetyError

QUICK_ITEMS = {"rare_candy": "Caramelo Raro", "heart_scale": "Escama Corazón"}


def describe(change):
    if (
        set(change) != {"kind", "item", "quantity", "expected_count"}
        or change["item"] not in QUICK_ITEMS
        or type(change["quantity"]) is not int
        or type(change["expected_count"]) is not int
        or change["quantity"] < 1
        or change["expected_count"] < 0
    ):
        raise WriteSafetyError("INVALID_WRITE_INTENT")
    return (
        f"Añadir {change['quantity']} × {QUICK_ITEMS[change['item']]} "
        f"(ahora tienes {change['expected_count']}). Solo cambia esa bolsa; "
        "se conserva una copia del archivo original."
    )


def inventory_view(native, data):
    reading = native.inventory(data)
    return {
        "game": reading["game"],
        "source_sha256": reading["source_sha256"],
        "items": {
            name: reading["items"][name] | {"name": label}
            for name, label in QUICK_ITEMS.items()
        },
    }


def quick_item_intent(native, data, item, quantity):
    if item not in QUICK_ITEMS or type(quantity) is not int or quantity < 1:
        raise WriteSafetyError("INVALID_QUICK_ITEM")
    reading = native.inventory(data)
    current = reading["items"][item]
    if quantity > current["addable"]:
        raise WriteSafetyError(
            "INVENTORY_FULL" if current["addable"] == 0 else "INVENTORY_LIMIT"
        )
    if reading["source_sha256"] != sha256(data).hexdigest():
        raise WriteSafetyError("STALE_SOURCE")
    return WriteIntent.create(
        expected_sha256=reading["source_sha256"],
        game=reading["game"],
        trainer_key=reading["trainer_key"],
        mutation={
            "kind": "add_item",
            "item": item,
            "quantity": quantity,
            "expected_count": current["count"],
        },
    )
