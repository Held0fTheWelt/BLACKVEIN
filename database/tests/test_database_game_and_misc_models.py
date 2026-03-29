from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import GameCharacter, GameExperienceTemplate, GameSaveSlot


class TestGameCharacterModel:
    def test_game_character_defaults_and_to_dict(self, db, user_factory):
        user = user_factory()
        character = GameCharacter(user_id=user.id, name="shadow-tech", display_name="Shadow Tech", bio="Matrix specialist")
        db.session.add(character)
        db.session.commit()

        assert character.is_default is False
        assert character.is_archived is False
        payload = character.to_dict()
        assert payload["user_id"] == user.id
        assert payload["name"] == "shadow-tech"
        assert payload["display_name"] == "Shadow Tech"
        assert payload["bio"] == "Matrix specialist"
        assert payload["created_at"] is not None
        assert payload["updated_at"] is not None

    def test_deleting_user_cascades_game_characters(self, db, user_factory):
        user = user_factory()
        db.session.add(GameCharacter(user_id=user.id, name="operator", display_name="Operator"))
        db.session.commit()

        db.session.delete(user)
        db.session.commit()
        assert GameCharacter.query.count() == 0


class TestGameSaveSlotModel:
    def test_game_save_slot_unique_per_user_and_slot_key(self, db, user_factory):
        user = user_factory()
        slot = GameSaveSlot(user_id=user.id, slot_key="slot-a", title="Slot A", template_id="tmpl-a", status="active", metadata_json={"chapter": 1})
        db.session.add(slot)
        db.session.commit()

        db.session.add(GameSaveSlot(user_id=user.id, slot_key="slot-a", title="Duplicate", template_id="tmpl-b", status="active"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_game_save_slot_to_dict_maps_metadata_json_to_metadata(self, db, user_factory):
        user = user_factory()
        character = GameCharacter(user_id=user.id, name="ghost", display_name="Ghost")
        db.session.add(character)
        db.session.commit()

        slot = GameSaveSlot(
            user_id=user.id,
            character_id=character.id,
            slot_key="slot-1",
            title="First Run",
            template_id="god-of-carnage",
            template_title="God of Carnage",
            run_id="run-001",
            kind="solo_story",
            status="active",
            metadata_json={"scene": "living-room", "turn": 4},
        )
        db.session.add(slot)
        db.session.commit()

        payload = slot.to_dict()
        assert payload["character_id"] == character.id
        assert payload["metadata"] == {"scene": "living-room", "turn": 4}
        assert payload["template_id"] == "god-of-carnage"
        assert payload["created_at"] is not None

    def test_deleting_user_cascades_game_save_slots(self, db, user_factory):
        user = user_factory()
        db.session.add(GameSaveSlot(user_id=user.id, slot_key="slot-cascade", title="Cascade", template_id="tmpl", status="active"))
        db.session.commit()

        db.session.delete(user)
        db.session.commit()
        assert GameSaveSlot.query.count() == 0

    def test_deleting_character_sets_save_slot_character_id_to_null(self, db, user_factory):
        user = user_factory()
        character = GameCharacter(user_id=user.id, name="fox", display_name="Fox")
        db.session.add(character)
        db.session.commit()

        slot = GameSaveSlot(user_id=user.id, character_id=character.id, slot_key="slot-null", title="Null Character", template_id="tmpl", status="active")
        db.session.add(slot)
        db.session.commit()

        db.session.delete(character)
        db.session.commit()
        db.session.refresh(slot)

        assert slot.character_id is None


class TestGameExperienceTemplateModel:
    def test_game_experience_template_defaults_and_to_dict(self, db, user_factory):
        user = user_factory(role_name="admin")
        template = GameExperienceTemplate(
            template_id="god-of-carnage",
            slug="god-of-carnage",
            title="God of Carnage",
            kind="solo_story",
            summary="A chamber drama.",
            payload_json={"module": "god_of_carnage", "version": 1},
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        db.session.add(template)
        db.session.commit()

        payload = template.to_dict(include_payload=False)
        assert payload["template_id"] == "god-of-carnage"
        assert payload["slug"] == "god-of-carnage"
        assert payload["style_profile"] == "retro_pulp"
        assert payload["tags"] == []
        assert payload["source"] == "authored"
        assert payload["is_published"] is False
        assert "payload" not in payload

        payload_with_body = template.to_dict(include_payload=True)
        assert payload_with_body["payload"] == {"module": "god_of_carnage", "version": 1}

    def test_game_experience_template_requires_unique_template_id_and_slug(self, db):
        db.session.add(
            GameExperienceTemplate(
                template_id="tmpl-1",
                slug="slug-1",
                title="Template 1",
                kind="solo_story",
                payload_json={"a": 1},
            )
        )
        db.session.commit()

        db.session.add(
            GameExperienceTemplate(
                template_id="tmpl-1",
                slug="slug-2",
                title="Template 2",
                kind="solo_story",
                payload_json={"a": 2},
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add(
            GameExperienceTemplate(
                template_id="tmpl-2",
                slug="slug-1",
                title="Template 3",
                kind="solo_story",
                payload_json={"a": 3},
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
