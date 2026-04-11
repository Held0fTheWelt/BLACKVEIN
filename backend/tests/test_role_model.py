"""Coverage for app.models.role (to_dict, get_role_by_name)."""
import pytest
from app.extensions import db
from app.models import Role
from app.models.role import get_role_by_name


@pytest.fixture
def extra_role(app):
    with app.app_context():
        r = Role(name="cov_role_x", description="d1", default_role_level=7)
        db.session.add(r)
        db.session.commit()
        db.session.refresh(r)
        yield r


def test_to_dict_includes_optional_fields(app, extra_role):
    with app.app_context():
        d = extra_role.to_dict()
        assert d["description"] == "d1"
        assert d["default_role_level"] == 7


def test_to_dict_omits_none_optional(app):
    with app.app_context():
        r = Role(name="cov_role_y", description=None, default_role_level=None)
        db.session.add(r)
        db.session.commit()
        db.session.refresh(r)
        d = r.to_dict()
        assert "description" not in d
        assert "default_role_level" not in d


def test_get_role_by_name_invalid_inputs(app):
    with app.app_context():
        assert get_role_by_name(None) is None
        assert get_role_by_name("") is None
        assert get_role_by_name(123) is None  # type: ignore


def test_get_role_by_name_case_insensitive(app, extra_role):
    with app.app_context():
        assert get_role_by_name("COV_ROLE_X").id == extra_role.id
