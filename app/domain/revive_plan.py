"""The one definition of a revive target, shared by the Launcher and the verifier.

Box numbers are as the trainer sees them (Caja 7 is 7); the native intent is
zero-based (6). Both sides must derive the exact same plan from the same bytes:
the verifier re-derives it and compares the result byte for byte.
"""

from hashlib import sha256


def revive_destination(boxes, dead_box):
    """First free slot, zero-based, in the boxes before the dead one (max Caja 7)."""
    limit = min(dead_box, 8)
    for box in sorted(boxes, key=lambda b: b.number):
        if 1 <= box.number < limit:
            for index, slot in enumerate(box.slots):
                if slot is None:
                    return (box.number - 1, index)
    return None


def trainer_key(observation):
    t = observation.trainer
    return sha256(
        "\0".join(
            map(str, (observation.game, t.name, t.tid, t.sid, t.gender, t.language))
        ).encode()
    ).hexdigest()


def revive_mutation(
    dead_box, slot_number, pid, encryption_constant, destination, authorization_id
):
    return {
        "kind": "revive",
        "location": "box",
        "box_index": dead_box - 1,
        "slot_index": slot_number - 1,
        "target_pid": pid,
        "target_ec": encryption_constant,
        "destination_box_index": destination[0],
        "destination_slot_index": destination[1],
        "authorization_id": authorization_id,
    }
