"""Parser for candidate_context.md.

Format (see candidate_context.example.md at the repo root):

    ## Profile                 -> `- key: value` bullets
    ## Education / Experience / Projects / Courses
    ### <title>                -> one item; `- key: value` bullets below it,
                                  other lines become its description
    ## Skills                  -> one `- skill` bullet per skill

Any other `##` section is ignored, so the file can carry free-form context too.

Status values are copied verbatim (only case/spacing is normalised, e.g.
"In Progress" -> "in-progress"). Anything unrecognised is an error; the parser
never guesses a status.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from app.models import ItemStatus, ItemType, ProfileBase, ProfileItemBase

SECTION_TYPES: dict[str, ItemType] = {
    "education": ItemType.EDUCATION,
    "experience": ItemType.JOB,
    "projects": ItemType.PROJECT,
    "courses": ItemType.COURSE,
    "skills": ItemType.SKILL,
}

PROFILE_KEYS = {
    "name": "full_name",
    "full_name": "full_name",
    "headline": "headline",
    "email": "email",
    "location": "location",
    "german_level": "german_level",
    "german": "german_level",
}

ITEM_KEYS = {
    "organization": "organization",
    "organisation": "organization",
    "company": "organization",
    "institution": "organization",
    "period": "period",
    "dates": "period",
    "status": "status",
    "stack": "stack",
    "metrics": "metrics",
    "link": "link",
    "url": "link",
    "description": "description",
}

LIST_SEPARATORS = {"stack": ",", "metrics": ";"}

_BULLET = re.compile(r"^(?P<indent>\s*)[-*]\s+(?P<body>.*)$")
_KEY_VALUE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z _-]*?)\s*:\s*(?P<value>.*)$")


class ContextParseError(ValueError):
    pass


@dataclass
class CandidateContext:
    profile: ProfileBase
    items: list[ProfileItemBase]
    warnings: list[str] = field(default_factory=list)


@dataclass
class _RawItem:
    type: ItemType
    title: str
    line: int
    fields: dict[str, str | list[str]] = field(default_factory=dict)
    prose: list[str] = field(default_factory=list)


def _clean(value: str) -> str:
    return value.strip().strip("*`_").strip()


def _norm_key(key: str) -> str:
    return re.sub(r"[\s-]+", "_", key.strip().lower())


def normalize_status(raw: str, line: int) -> ItemStatus:
    token = re.sub(r"[\s_]+", "-", _clean(raw).lower())
    try:
        return ItemStatus(token)
    except ValueError:
        allowed = ", ".join(s.value for s in ItemStatus)
        raise ContextParseError(
            f"line {line}: unknown status {raw.strip()!r} (allowed: {allowed})"
        ) from None


def parse_candidate_context(text: str) -> CandidateContext:
    warnings: list[str] = []
    profile_fields: dict[str, str] = {}
    raw_items: list[_RawItem] = []

    section: str | None = None
    current: _RawItem | None = None
    list_key: str | None = None  # key whose value continues as nested bullets

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue

        if stripped.startswith("## ") and not stripped.startswith("### "):
            name = _clean(stripped[3:]).lower()
            section = name if name == "profile" or name in SECTION_TYPES else None
            current, list_key = None, None
            continue
        if stripped.startswith("# "):
            continue
        if section is None:
            continue

        if stripped.startswith("### "):
            if section in ("profile", "skills"):
                raise ContextParseError(f"line {lineno}: '###' items are not allowed under ## {section}")
            current = _RawItem(SECTION_TYPES[section], _clean(stripped[4:]), lineno)
            raw_items.append(current)
            list_key = None
            continue

        bullet = _BULLET.match(line)

        if section == "skills":
            if bullet:
                raw_items.append(_RawItem(ItemType.SKILL, _clean(bullet["body"]), lineno))
            continue

        if section == "profile":
            kv = _KEY_VALUE.match(bullet["body"]) if bullet else None
            if not kv:
                continue
            key = _norm_key(kv["key"])
            if key not in PROFILE_KEYS:
                warnings.append(f"line {lineno}: ignoring unknown profile key {kv['key']!r}")
                continue
            # Values are stored verbatim (e.g. german_level "B1 (certified)").
            profile_fields[PROFILE_KEYS[key]] = _clean(kv["value"])
            continue

        # Item sections.
        if current is None:
            warnings.append(f"line {lineno}: text outside any ### item in ## {section}, ignored")
            continue
        if bullet and bullet["indent"] and list_key:
            values = current.fields.setdefault(list_key, [])
            assert isinstance(values, list)
            values.append(_clean(bullet["body"]))
            continue
        kv = _KEY_VALUE.match(bullet["body"]) if bullet else None
        if bullet and kv and _norm_key(kv["key"]) in ITEM_KEYS:
            key = ITEM_KEYS[_norm_key(kv["key"])]
            value = _clean(kv["value"])
            if key in current.fields:
                raise ContextParseError(f"line {lineno}: duplicate field {key!r} in {current.title!r}")
            if key in LIST_SEPARATORS:
                current.fields[key] = [v.strip() for v in value.split(LIST_SEPARATORS[key]) if v.strip()]
                list_key = key if not value else None
            else:
                current.fields[key] = value
                list_key = None
            continue
        # Anything else (prose, bullets with unknown keys) becomes the description.
        list_key = None
        current.prose.append(bullet["body"].strip() if bullet else stripped)

    return CandidateContext(
        profile=_build_profile(profile_fields),
        items=_build_items(raw_items),
        warnings=warnings,
    )


def _build_profile(fields: dict[str, str]) -> ProfileBase:
    for required in ("full_name", "german_level"):
        if not fields.get(required):
            raise ContextParseError(f"## Profile is missing required field {required!r}")
    return ProfileBase(**{k: (v or None) for k, v in fields.items()})


def _build_items(raw_items: list[_RawItem]) -> list[ProfileItemBase]:
    items: list[ProfileItemBase] = []
    seen: set[tuple[ItemType, str]] = set()
    positions: dict[ItemType, int] = {}

    for raw in raw_items:
        if not raw.title:
            raise ContextParseError(f"line {raw.line}: item has an empty title")
        key = (raw.type, raw.title)
        if key in seen:
            raise ContextParseError(f"line {raw.line}: duplicate {raw.type} {raw.title!r}")
        seen.add(key)

        data = dict(raw.fields)
        raw_status = data.pop("status", None)
        if raw.type is ItemType.SKILL:
            status = None
        elif not raw_status:
            raise ContextParseError(
                f"line {raw.line}: {raw.type} {raw.title!r} has no status "
                "(add '- status: in-progress|completed|planned|paused')"
            )
        else:
            status = normalize_status(str(raw_status), raw.line)

        if raw.prose and not data.get("description"):
            data["description"] = "\n".join(raw.prose)

        position = positions.get(raw.type, 0)
        positions[raw.type] = position + 1
        try:
            items.append(
                ProfileItemBase(
                    type=raw.type,
                    title=raw.title,
                    status=status,
                    position=position,
                    **{k: (v or None) if isinstance(v, str) else v for k, v in data.items()},
                )
            )
        except ValidationError as exc:
            raise ContextParseError(f"line {raw.line}: invalid item {raw.title!r}: {exc}") from exc
    return items


def load_candidate_context(path: Path) -> CandidateContext:
    if not path.is_file():
        raise ContextParseError(f"{path} not found")
    return parse_candidate_context(path.read_text(encoding="utf-8"))
