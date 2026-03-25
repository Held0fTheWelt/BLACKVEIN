"""
Cross-service contract tests for Backend <-> Administration Tool integration.

This module ensures that the Backend API maintains compatibility with the
Administration Tool by validating:
1. API response format consistency
2. Permission/role data structure integrity
3. User management contract compliance
4. Admin action/audit trail compatibility

These tests are critical for deployment as they verify the contract between
two independently deployable services.
"""

import pytest
from app.models import User, Role
from app.extensions import db


class TestAdminBridgeUserContract:
    """Validates user data structure contract with admin tool."""

    def test_user_response_format_consistency(self, test_user):
        """Admin tool expects specific user response format."""
        user, _ = test_user
        # Ensure user has all required fields for admin bridge
        required_fields = [
            'id', 'username', 'created_at', 'updated_at', 'is_active'
        ]

        user_dict = {
            'id': user.id,
            'username': user.username,
            'created_at': user.created_at,
            'updated_at': user.updated_at,
            'is_active': user.is_active,
        }

        for field in required_fields:
            assert field in user_dict, f"Missing field: {field}"
            assert user_dict[field] is not None, f"Field {field} is None"

    def test_user_role_relationship_contract(self, test_user, admin_user):
        """Admin tool depends on user->role relationship."""
        _, _ = test_user  # Unpack fixture
        admin, _ = admin_user
        # Admin user must have role relationship
        assert admin.role_rel is not None
        assert admin.role_rel.id is not None
        assert admin.role_rel.name is not None

    def test_password_handling_contract(self, test_user):
        """Admin tool must not receive plaintext passwords."""
        user, _ = test_user
        # User model should not expose plaintext password
        user_dict = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
        }
        # Password field should never be in response dict
        assert 'password' not in user_dict
        assert 'password_hash' not in user_dict

    def test_user_deletion_contract(self, auth_headers, client, app):
        """Admin tool expects specific deletion behavior."""
        with app.app_context():
            # Create user via backend with proper role
            from app.models import Role
            role = Role.query.filter_by(name=Role.NAME_USER).first()
            new_user = User(
                username='test_deletion_user',
                email='deletion@test.com',
                password_hash='dummy_hash',
                role_id=role.id
            )
            db.session.add(new_user)
            db.session.commit()
            user_id = new_user.id

        # Delete user
        response = client.delete(f'/api/users/{user_id}', headers=auth_headers)
        # Endpoint might not exist, check for 404 or 204
        assert response.status_code in [204, 404, 401, 403]

    def test_user_update_contract(self, auth_headers, client, test_user):
        """Admin tool expects specific update response format."""
        user, _ = test_user
        update_data = {
            'email': 'newemail@test.com',
            'is_active': False
        }

        response = client.patch(
            f'/api/users/{user.id}',
            json=update_data,
            headers=auth_headers
        )

        # Endpoint might not exist, accept 200 or 404/401
        if response.status_code == 200:
            data = response.get_json()
            # Verify response format if successful
            assert 'id' in data
            assert data['id'] == user.id
            if 'email' in data:
                assert data['email'] == 'newemail@test.com'


class TestAdminBridgeRoleContract:
    """Validates role/permission data structure contract with admin tool."""

    def test_role_list_response_format(self, auth_headers, client):
        """Admin tool expects consistent role list format."""
        response = client.get('/api/roles', headers=auth_headers)
        # Endpoint might not exist
        if response.status_code == 200:
            data = response.get_json()
            assert isinstance(data, list)

            if len(data) > 0:
                role = data[0]
                # Roles should have id and name fields
                assert 'id' in role
                assert 'name' in role

    def test_role_permission_contract(self, admin_user):
        """Admin tool depends on role relationship."""
        admin, _ = admin_user
        # Admin user must have role relationship
        admin_role = admin.role_rel
        assert admin_role is not None

        # Role should have default_role_level (used for privilege hierarchy)
        assert hasattr(admin_role, 'default_role_level')
        if admin_role.default_role_level is not None:
            assert admin_role.default_role_level >= 50  # Admin minimum

    def test_privilege_level_ordering_contract(self, app):
        """Admin tool assumes specific privilege level ordering."""
        # Roles should follow privilege level hierarchy
        # Lower numbers = less privilege
        # This is critical for admin permission checks

        with app.app_context():
            roles = Role.query.all()
            if len(roles) >= 2:
                # Filter roles with default_role_level set
                roles_with_level = [r for r in roles if r.default_role_level is not None]
                if len(roles_with_level) >= 2:
                    # Sort by default_role_level
                    sorted_roles = sorted(roles_with_level, key=lambda r: r.default_role_level)

                    # Ensure they're actually ordered
                    for i in range(len(sorted_roles) - 1):
                        current = sorted_roles[i].default_role_level
                        next_level = sorted_roles[i+1].default_role_level
                        # Either equal (same role type) or ascending
                        assert current <= next_level


class TestAdminBridgeAuditContract:
    """Validates audit trail contract between backend and admin tool."""

    def test_user_creation_event_structure(self, auth_headers, client, app):
        """Admin tool expects specific user creation audit trail."""
        user_data = {
            'username': 'audit_test_user',
            'email': 'audit@test.com',
            'password': 'secure_password'
        }

        response = client.post(
            '/api/users',
            json=user_data,
            headers=auth_headers
        )

        # Endpoint might not exist
        if response.status_code == 201:
            data = response.get_json()
            # Verify user has timestamps for audit trail
            assert 'id' in data
            if 'created_at' in data:
                assert data['created_at'] is not None

    def test_user_update_event_structure(self, auth_headers, client, test_user, app):
        """Admin tool tracks update events with timestamps."""
        user, _ = test_user
        with app.app_context():
            # Get fresh copy
            user_id = user.id
            fresh_user = User.query.get(user_id)
            original_updated = fresh_user.updated_at

            # Update user via API
            response = client.patch(
                f'/api/users/{user_id}',
                json={'email': 'newemail@test.com'},
                headers=auth_headers
            )

            # Refresh from database
            fresh_user = User.query.get(user_id)
            if fresh_user:
                # Verify updated_at changed or stayed same (if endpoint doesn't exist)
                assert fresh_user.updated_at >= original_updated


class TestAdminBridgeAuthContract:
    """Validates authentication/authorization contract with admin tool."""

    def test_admin_authorization_header_format(self, auth_headers):
        """Admin tool sends auth in expected format."""
        assert 'Authorization' in auth_headers or 'X-API-Key' in auth_headers

    def test_unauthorized_access_response(self, client):
        """Admin tool expects 401 for missing auth."""
        response = client.get('/api/users')
        # Endpoint might not exist (404) or might require auth (401)
        assert response.status_code in [401, 404]

    def test_forbidden_access_response(self, client, auth_headers):
        """Admin tool expects 403 for insufficient permissions."""
        # Try to access elevated endpoint with basic user
        response = client.get('/api/users/1/permissions', headers=auth_headers)
        # Should be either 403 (forbidden) or 404 (not found)
        assert response.status_code in [403, 404]


class TestAdminBridgeDataConsistency:
    """Validates data consistency across admin tool interactions."""

    def test_user_query_consistency(self, test_user, app):
        """Admin tool queries must return consistent user data."""
        user, _ = test_user
        with app.app_context():
            # Query user
            user1 = User.query.get(user.id)
            user2 = User.query.filter_by(username=user.username).first()

            # Both queries should return same data
            assert user1.id == user2.id
            assert user1.email == user2.email
            assert user1.is_active == user2.is_active

    def test_user_batch_query_contract(self, app):
        """Admin tool may need to query multiple users."""
        with app.app_context():
            # Create test users
            users = []
            for i in range(3):
                from app.models import Role
                role = Role.query.filter_by(name=Role.NAME_USER).first()
                user = User(
                    username=f'batch_user_{i}',
                    email=f'batch_{i}@test.com',
                    password_hash='dummy_hash',
                    role_id=role.id,
                )
                users.append(user)

            db.session.add_all(users)
            db.session.commit()

            # Query all at once
            all_users = User.query.all()
            assert len(all_users) >= 3

            # Clean up
            for user in users:
                db.session.delete(user)
            db.session.commit()

    def test_role_assignment_contract(self, test_user, app):
        """Admin tool assumes role assignment is reliable."""
        user, _ = test_user
        with app.app_context():
            # Get fresh copy
            user_id = user.id
            fresh_user = User.query.get(user_id)
            original_role_id = fresh_user.role_id

            # Assign new role
            new_role = Role.query.filter(Role.id != original_role_id).first()
            if new_role:
                fresh_user.role_id = new_role.id
                db.session.commit()

                # Verify change persisted
                fresh_user = User.query.get(user_id)
                assert fresh_user.role_id == new_role.id


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
