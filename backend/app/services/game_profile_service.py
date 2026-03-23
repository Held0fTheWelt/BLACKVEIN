from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.extensions import db
from app.models import GameCharacter, GameSaveSlot, User


class GameProfileError(ValueError):
    pass


class NotFoundError(GameProfileError):
    pass


class OwnershipError(GameProfileError):
    pass


class ValidationError(GameProfileError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def list_characters_for_user(user_id: int, *, include_archived: bool = False) -> list[GameCharacter]:
    stmt = select(GameCharacter).where(GameCharacter.user_id == user_id)
    if not include_archived:
        stmt = stmt.where(GameCharacter.is_archived.is_(False))
    stmt = stmt.order_by(GameCharacter.is_default.desc(), GameCharacter.updated_at.desc(), GameCharacter.id.asc())
    return list(db.session.scalars(stmt).all())


def get_character_for_user(user_id: int, character_id: int) -> GameCharacter:
    character = db.session.get(GameCharacter, int(character_id))
    if character is None:
        raise NotFoundError("Character not found.")
    if character.user_id != user_id:
        raise OwnershipError("Character does not belong to this user.")
    return character


def create_character_for_user(
    user: User,
    *,
    name: str,
    display_name: str | None = None,
    bio: str | None = None,
    is_default: bool = False,
) -> GameCharacter:
    clean_name = (name or "").strip()
    clean_display = (display_name or clean_name or user.username or "Character").strip()
    clean_bio = (bio or "").strip() or None
    if not clean_name:
        raise ValidationError("Character name is required.")
    if len(clean_name) > 120:
        raise ValidationError("Character name is too long.")
    if len(clean_display) > 120:
        raise ValidationError("Display name is too long.")
    if clean_bio and len(clean_bio) > 4000:
        raise ValidationError("Character bio is too long.")

    existing = list_characters_for_user(user.id, include_archived=True)
    if any(c.name.lower() == clean_name.lower() for c in existing if not c.is_archived):
        raise ValidationError("You already have a character with that name.")

    make_default = bool(is_default) or not any(not c.is_archived for c in existing)
    if make_default:
        for character in existing:
            character.is_default = False

    character = GameCharacter(
        user_id=user.id,
        name=clean_name,
        display_name=clean_display,
        bio=clean_bio,
        is_default=make_default,
        is_archived=False,
    )
    db.session.add(character)
    db.session.commit()
    return character


def update_character_for_user(
    user_id: int,
    character_id: int,
    *,
    name: str | None = None,
    display_name: str | None = None,
    bio: str | None = None,
    is_default: bool | None = None,
    is_archived: bool | None = None,
) -> GameCharacter:
    character = get_character_for_user(user_id, character_id)

    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("Character name is required.")
        if len(clean_name) > 120:
            raise ValidationError("Character name is too long.")
        siblings = list_characters_for_user(user_id, include_archived=True)
        if any(c.id != character.id and c.name.lower() == clean_name.lower() and not c.is_archived for c in siblings):
            raise ValidationError("You already have a character with that name.")
        character.name = clean_name
    if display_name is not None:
        clean_display = display_name.strip()
        if not clean_display:
            raise ValidationError("Display name is required.")
        if len(clean_display) > 120:
            raise ValidationError("Display name is too long.")
        character.display_name = clean_display
    if bio is not None:
        clean_bio = bio.strip() or None
        if clean_bio and len(clean_bio) > 4000:
            raise ValidationError("Character bio is too long.")
        character.bio = clean_bio
    if is_archived is not None:
        character.is_archived = bool(is_archived)
        if character.is_archived:
            character.is_default = False
    if is_default is True:
        for sibling in list_characters_for_user(user_id, include_archived=True):
            sibling.is_default = sibling.id == character.id
        character.is_archived = False
        character.is_default = True

    db.session.commit()

    active_characters = [c for c in list_characters_for_user(user_id) if not c.is_archived]
    if active_characters and not any(c.is_default for c in active_characters):
        active_characters[0].is_default = True
        db.session.commit()

    return character


def touch_character_last_used(user_id: int, character_id: int | None) -> None:
    if not character_id:
        return
    character = get_character_for_user(user_id, int(character_id))
    character.last_used_at = _utc_now()
    db.session.commit()


def list_save_slots_for_user(user_id: int) -> list[GameSaveSlot]:
    stmt = (
        select(GameSaveSlot)
        .where(GameSaveSlot.user_id == user_id)
        .order_by(GameSaveSlot.updated_at.desc(), GameSaveSlot.id.desc())
    )
    return list(db.session.scalars(stmt).all())


def get_save_slot_for_user(user_id: int, slot_id: int) -> GameSaveSlot:
    slot = db.session.get(GameSaveSlot, int(slot_id))
    if slot is None:
        raise NotFoundError("Save slot not found.")
    if slot.user_id != user_id:
        raise OwnershipError("Save slot does not belong to this user.")
    return slot


def upsert_save_slot_for_user(
    user_id: int,
    *,
    slot_key: str,
    title: str,
    template_id: str,
    template_title: str | None = None,
    run_id: str | None = None,
    kind: str | None = None,
    status: str | None = None,
    character_id: int | None = None,
    metadata: dict | None = None,
) -> GameSaveSlot:
    clean_slot_key = (slot_key or "").strip().lower()
    clean_title = (title or "").strip()
    clean_template_id = (template_id or "").strip()
    if not clean_slot_key:
        raise ValidationError("slot_key is required.")
    if not clean_title:
        raise ValidationError("title is required.")
    if not clean_template_id:
        raise ValidationError("template_id is required.")
    if len(clean_slot_key) > 64:
        raise ValidationError("slot_key is too long.")
    if len(clean_title) > 140:
        raise ValidationError("title is too long.")
    if character_id is not None:
        get_character_for_user(user_id, int(character_id))

    slot = db.session.scalar(
        select(GameSaveSlot).where(
            GameSaveSlot.user_id == user_id,
            GameSaveSlot.slot_key == clean_slot_key,
        )
    )
    if slot is None:
        slot = GameSaveSlot(user_id=user_id, slot_key=clean_slot_key)
        db.session.add(slot)

    slot.title = clean_title
    slot.template_id = clean_template_id
    slot.template_title = (template_title or clean_title).strip() or None
    slot.run_id = (run_id or "").strip() or None
    slot.kind = (kind or "").strip() or None
    slot.status = (status or "active").strip() or "active"
    slot.character_id = int(character_id) if character_id is not None else None
    slot.metadata_json = metadata or {}
    slot.last_played_at = _utc_now()
    db.session.commit()
    return slot


def delete_save_slot_for_user(user_id: int, slot_id: int) -> None:
    slot = get_save_slot_for_user(user_id, slot_id)
    db.session.delete(slot)
    db.session.commit()
