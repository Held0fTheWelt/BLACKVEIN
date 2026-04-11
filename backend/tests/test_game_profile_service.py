"""Tests for app.services.game_profile_service (characters and save slots)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Role, User
from app.services.game_profile_service import (
    NotFoundError,
    OwnershipError,
    ValidationError,
    create_character_for_user,
    delete_save_slot_for_user,
    get_character_for_user,
    get_save_slot_for_user,
    list_characters_for_user,
    list_save_slots_for_user,
    touch_character_last_used,
    update_character_for_user,
    upsert_save_slot_for_user,
)


@pytest.fixture
def second_user(app):
    with app.app_context():
        role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="second_game_profile_user",
            password_hash=generate_password_hash("Secret123"),
            role_id=role.id,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


class TestGameProfileCharacterFlows:
    def test_create_list_and_validate_characters(self, app, test_user):
        user, _ = test_user
        with app.app_context():
            first = create_character_for_user(user, name="Bruno", display_name="Bruno Houille", bio="First")
            second = create_character_for_user(user, name="Ferdinand", display_name="Ferdinand Reille")

            active = list_characters_for_user(user.id)
            archived_inclusive = list_characters_for_user(user.id, include_archived=True)

            assert first.is_default is True
            assert second.is_default is False
            assert [c.name for c in active] == ["Bruno", "Ferdinand"]
            assert len(archived_inclusive) == 2

            with pytest.raises(ValidationError, match="Character name is required"):
                create_character_for_user(user, name="   ")
            with pytest.raises(ValidationError, match="Character name is too long"):
                create_character_for_user(user, name="x" * 121)
            with pytest.raises(ValidationError, match="Display name is too long"):
                create_character_for_user(user, name="Valid", display_name="y" * 121)
            with pytest.raises(ValidationError, match="Character bio is too long"):
                create_character_for_user(user, name="Valid", bio="b" * 4001)
            with pytest.raises(ValidationError, match="already have a character"):
                create_character_for_user(user, name="bruno")

    def test_update_archiving_and_default_reassignment(self, app, test_user):
        user, _ = test_user
        with app.app_context():
            first = create_character_for_user(user, name="Veronique", display_name="Veronique")
            second = create_character_for_user(user, name="Annette", display_name="Annette")

            archived = update_character_for_user(user.id, first.id, is_archived=True)
            refreshed_second = get_character_for_user(user.id, second.id)
            assert archived.is_archived is True
            assert archived.is_default is False
            assert refreshed_second.is_default is True

            restored = update_character_for_user(
                user.id,
                first.id,
                name="Veronique Updated",
                display_name="Veronique H.",
                bio="Writer",
                is_default=True,
            )
            refreshed_second = get_character_for_user(user.id, second.id)
            assert restored.name == "Veronique Updated"
            assert restored.display_name == "Veronique H."
            assert restored.bio == "Writer"
            assert restored.is_archived is False
            assert restored.is_default is True
            assert refreshed_second.is_default is False

            with pytest.raises(ValidationError, match="already have a character"):
                update_character_for_user(user.id, second.id, name="veronique updated")
            with pytest.raises(ValidationError, match="Display name is required"):
                update_character_for_user(user.id, second.id, display_name="   ")
            with pytest.raises(ValidationError, match="Character bio is too long"):
                update_character_for_user(user.id, second.id, bio="z" * 4001)

    def test_get_character_raises_not_found_and_ownership(self, app, test_user, second_user):
        user, _ = test_user
        with app.app_context():
            character = create_character_for_user(user, name="Michel")

            with pytest.raises(NotFoundError, match="Character not found"):
                get_character_for_user(user.id, 999999)
            with pytest.raises(OwnershipError, match="does not belong"):
                get_character_for_user(second_user.id, character.id)

    def test_touch_character_last_used_updates_timestamp(self, app, test_user, monkeypatch):
        user, _ = test_user
        fixed_now = datetime(2026, 3, 29, 18, 0, tzinfo=timezone.utc)
        monkeypatch.setattr("app.services.game_profile_service._utc_now", lambda: fixed_now)

        with app.app_context():
            character = create_character_for_user(user, name="Alain")
            touch_character_last_used(user.id, None)
            touch_character_last_used(user.id, character.id)
            refreshed = get_character_for_user(user.id, character.id)
            assert refreshed.last_used_at.replace(tzinfo=timezone.utc) == fixed_now


class TestGameProfileSaveSlots:
    def test_upsert_list_get_and_delete_save_slots(self, app, test_user):
        user, _ = test_user
        with app.app_context():
            character = create_character_for_user(user, name="Solo")
            created = upsert_save_slot_for_user(
                user.id,
                slot_key=" SLOT-A ",
                title=" Apartment Checkpoint ",
                template_id=" god_of_carnage_solo ",
                template_title=" God of Carnage ",
                run_id=" run-1 ",
                kind=" solo_story ",
                status=" active ",
                character_id=character.id,
                metadata={"beat": "arrival"},
            )
            updated = upsert_save_slot_for_user(
                user.id,
                slot_key="slot-a",
                title="Apartment Checkpoint Updated",
                template_id="god_of_carnage_solo",
                template_title="God of Carnage",
                run_id="run-2",
                kind="solo_story",
                status="paused",
                character_id=character.id,
                metadata={"beat": "apology"},
            )
            newer = upsert_save_slot_for_user(
                user.id,
                slot_key="slot-b",
                title="Second Slot",
                template_id="god_of_carnage_solo",
            )

            listed = list_save_slots_for_user(user.id)
            fetched = get_save_slot_for_user(user.id, updated.id)

            assert created.id == updated.id
            assert fetched.run_id == "run-2"
            assert fetched.metadata_json == {"beat": "apology"}
            assert listed[0].slot_key == newer.slot_key
            assert listed[1].slot_key == "slot-a"

            delete_save_slot_for_user(user.id, fetched.id)
            remaining = list_save_slots_for_user(user.id)
            assert [slot.slot_key for slot in remaining] == ["slot-b"]

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"slot_key": "", "title": "T", "template_id": "tpl"}, "slot_key is required"),
            ({"slot_key": "slot", "title": "", "template_id": "tpl"}, "title is required"),
            ({"slot_key": "slot", "title": "T", "template_id": ""}, "template_id is required"),
            ({"slot_key": "x" * 65, "title": "T", "template_id": "tpl"}, "slot_key is too long"),
            ({"slot_key": "slot", "title": "y" * 141, "template_id": "tpl"}, "title is too long"),
        ],
    )
    def test_upsert_save_slot_validation_errors(self, app, test_user, kwargs, message):
        user, _ = test_user
        with app.app_context():
            with pytest.raises(ValidationError, match=message):
                upsert_save_slot_for_user(user.id, **kwargs)

    def test_get_save_slot_raises_not_found_and_ownership(self, app, test_user, second_user):
        user, _ = test_user
        with app.app_context():
            slot = upsert_save_slot_for_user(
                user.id,
                slot_key="owned-slot",
                title="Owned",
                template_id="god_of_carnage_solo",
            )

            with pytest.raises(NotFoundError, match="Save slot not found"):
                get_save_slot_for_user(user.id, 999999)
            with pytest.raises(OwnershipError, match="does not belong"):
                get_save_slot_for_user(second_user.id, slot.id)
