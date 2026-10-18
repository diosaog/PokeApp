"""Private PK6 evidence (X/Y/ORAS), separate from competitive 023 identity.

The historical class name is kept for local journal/import compatibility.
"""

from dataclasses import dataclass
from datetime import date

from app.domain.pokemon_identity import digest


@dataclass(frozen=True)
class ObservedXYIdentity:
    schema_version: int
    format: int
    pid: int
    ot_tid: int
    ot_sid: int
    origin_version: int
    language: int
    ot_name: str
    ot_gender: int
    met_location: int | None = None
    met_level: int | None = None
    egg_location: int | None = None
    met_date: str | None = None
    egg_date: str | None = None
    encryption_constant: int | None = None
    ivs: tuple[int, ...] = ()

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported_identity_evidence")
        if type(self.format) is not int or self.format != 6:
            raise ValueError("unsupported_identity_format")
        for name, upper in (
            ("pid", 2**32 - 1),
            ("encryption_constant", 2**32 - 1),
            ("ot_tid", 65535),
            ("ot_sid", 65535),
            ("origin_version", 255),
            ("language", 255),
            ("ot_gender", 1),
        ):
            value = getattr(self, name)
            if type(value) is not int or not 0 <= value <= upper:
                raise ValueError("invalid_identity_" + name)
        if (
            not isinstance(self.ot_name, str)
            or not self.ot_name
            or not self.origin_version
            or not self.language
        ):
            raise ValueError("incomplete_identity_evidence")
        object.__setattr__(self, "ivs", tuple(self.ivs))
        if len(self.ivs) != 6 or any(
            type(v) is not int or not 0 <= v <= 31 for v in self.ivs
        ):
            raise ValueError("invalid_identity_ivs")
        for name in ("met_location", "met_level", "egg_location"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("invalid_identity_" + name)
        for value in (self.met_date, self.egg_date):
            if value is not None:
                date.fromisoformat(value)

    @property
    def candidate_key(self) -> str:
        # Local hints only. Same-PID duplicates still remain ambiguous. Unlike
        # PK3/4/5, PK6 has an independent EC; a changed EC cannot silently match.
        return digest(
            [
                self.schema_version,
                self.format,
                self.pid,
                self.ot_tid,
                self.ot_sid,
                self.origin_version,
                self.language,
                self.ot_name,
                self.ot_gender,
                self.encryption_constant,
            ]
        )
