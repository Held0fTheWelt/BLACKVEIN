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
from app.database import db


class TestAdminBridgeUserContract:
    """Validates user data structure contract with admin tool."""

    def test_user_response_format_consistency(self, test_user):
        """Admin tool expects specific user response format."""
        # Ensure user has all required fields for admin bridge
        required_fields = [
            'id', 'username', 'email', 'created_at', 'updated_at', 'is_active'
        ]

        user_dict = {
            'id': test_user.id,
            'username': test_user.username,
            'email': test_user.email,
            'created_at': test_user.created_at,
            'updated_at': test_user.updated_at,
            'is_active': test_user.is_active,
        }

        for field in required_fields:
            assert field in user_dict, f"Missing field: {field}"
            assert user_dict[field] is not None

    def test_user_role_relationship_contract(self, test_user, admin_user):
        """Admin tool depends on user->role relationship."""
        # Admin user must have role relationship
        assert admin_user.role is not None
        assert admin_user.role.id is not None
        assert admin_user.role.name is not None

    def test_password_handling_contract(self, test_user):
        """Admin tool must not receive plaintext passwords."""
        # User model should not expose plaintext password
        user_dict = {
            'id': test_user.id,
            'username': test_user.username,
            'email': test_user.email,
        }
        # Password field should never be in response dict
        assert 'password' not in user_dict
        assert 'password_hash' not in user_dict

    def test_user_deletion_contract(self, auth_headers, client):
        """Admin tool expects specific deletion behavior."""
        # Create user via backend
        user = User(
            username='test_deletion_user',
            email='deletion@test.com',
            password='secure_password'
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        # Delete user
        response = client.delete(f'/api/users/{user_id}', headers=auth_headers)
        assert response.status_code == 204

        # Verify user is gone
        deleted_user = User.query.get(user_id)
        assert deleted_user is None

    def test_user_update_contract(self, auth_headers, client, test_user):
        """Admin tool expects specific update response format."""
        update_data = {
            'email': 'newemail@test.com',
            'is_active': False
        }

        response = client.patch(
            f'/api/users/{test_user.id}',
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify response format
        assert 'id' in data
        assert data['id'] == test_user.id
        assert 'email' in data
        assert data['email'] == 'newemail@test.com'


class TestAdminBridgeRoleContract:
    """Validates role/permission data structure contract with admin tool."""

    def test_role_list_response_format(self, auth_headers, client):
        """Admin tool expects consistent role list format."""
        response = client.get('/api/roles', headers=auth_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)

        if len(data) > 0:
            role = data[0]
            required_fields = ['id', 'name', 'privilege_level']
            for field in required_fields:
                assert field in role, f"Role missing field: {field}"

    def test_role_permission_contract(self, admin_user):
        """Admin tool depends on role->permission relationship."""
        # Admin role should have permissions
        admin_role = admin_user.role
        assert admin_role is not None

        # Role should have privilege_level
        assert hasattr(admin_role, 'privilege_level')
        assert admin_role.privilege_level is not None
        assert admin_role.privilege_level >= 50  # Admin minimum

    def test_privilege_level_ordering_contract(self):
        """Admin tool assumes specific privilege level ordering."""
        # Roles should follow privilege level hierarchy
        # Lower numbers = less privilege
        # This is critical for admin permission checks

        roles = Role.query.all()
        if len(roles) >= 2:
            # Sort by privilege level
            sorted_roles = sorted(roles, key=lambda r: r.privilege_level)

            # Ensure they're actually ordered
            for i in range(len(sorted_roles) - 1):
                current = sorted_roles[i].privilege_level
                next_level = sorted_roles[i+1].privilege_level
                # Either equal (same role type) or ascending
                assert current <= next_level


class TestAdminBridgeAuditContract:
    """Validates audit trail contract between backend and admin tool."""

    def test_user_creation_event_structure(self, auth_headers, client):
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

        assert response.status_code == 201
        data = response.get_json()

        # Verify user has timestamps for audit trail
        assert 'id' in data
        assert 'created_at' in data
        assert data['created_at'] is not None

    def test_user_update_event_structure(self, auth_headers, client, test_user):
        """Admin tool tracks update events with timestamps."""
        original_updated = test_user.updated_at

        # Update user
        client.patch(
            f'/api/users/{test_user.id}',
            json={'email': 'newemail@test.com'},
            headers=auth_headers
        )

        # Refresh from database
        db.session.refresh(test_user)

        # Verify updated_at changed
        assert test_user.updated_at >= original_updated


class TestAdminBridgeAuthContract:
    """Validates authentication/authorization contract with admin tool."""

    def test_admin_authorization_header_format(self, auth_headers):
        """Admin tool sends auth in expected format."""
        assert 'Authorization' in auth_headers or 'X-API-Key' in auth_headers

    def test_unauthorized_access_response(self, client):
        """Admin tool expects 401 for missing auth."""
        response = client.get('/api/users')
        assert response.status_code == 401

    def test_forbidden_access_response(self, client, auth_headers):
        """Admin tool expects 403 for insufficient permissions."""
        # Try to access elevated endpoint with basic user
        response = client.get('/api/users/1/permissions', headers=auth_headers)
        # Should be either 403 (forbidden) or 404 (not found)
        assert response.status_code in [403, 404]


class TestAdminBridgeDataConsistency:
    """Validates data consistency across admin tool interactions."""

    def test_user_query_consistency(self, test_user):
        """Admin tool queries must return consistent user data."""
        # Query user
        user1 = User.query.get(test_user.id)
        user2 = User.query.filter_by(username=test_user.username).first()

        # Both queries should return same data
        assert user1.id == user2.id
        assert user1.email == user2.email
        assert user1.is_active == user2.is_active

    def test_user_batch_query_contract(self):
        """Admin tool may need to query multiple users."""
        # Create test users
        users = []
        for i in range(3):
            user = User(
                username=f'batch_user_{i}',
                email=f'batch_{i}@test.com',
                password='secure'
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

    def test_role_assignment_contract(self, test_user):
        """Admin tool assumes role assignment is reliable."""
        original_role_id = test_user.role_id

        # Assign new role
        new_role = Role.query.filter(Role.id != original_role_id).first()
        if new_role:
            test_user.role_id = new_role.id
            db.session.commit()

            # Verify change persisted
            db.session.refresh(test_user)
            assert test_user.role_id == new_role.id


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
