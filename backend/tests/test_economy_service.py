"""Tests for the game economy service with balance validation.

Tests cover:
- Points deduction with validation
- Currency deduction with validation
- Inventory item deduction with validation
- Resource deduction with validation
- Edge cases (zero balance, zero deduction, etc.)
"""
import pytest

from app.services.economy_service import (
    EconomyError,
    InsufficientBalanceError,
    InvalidAmountError,
    PlayerBalance,
    get_player_balance,
)


class TestValidateAmount:
    """Test amount validation."""

    def test_positive_integer_is_valid(self):
        """Positive integers should be valid."""
        from app.services.economy_service import validate_amount
        # Should not raise
        validate_amount(100)
        validate_amount(1)
        validate_amount(0.5)

    def test_negative_amount_raises_error(self):
        """Negative amounts should raise InvalidAmountError."""
        from app.services.economy_service import validate_amount
        with pytest.raises(InvalidAmountError):
            validate_amount(-50)

    def test_zero_amount_raises_error(self):
        """Zero amount should raise InvalidAmountError."""
        from app.services.economy_service import validate_amount
        with pytest.raises(InvalidAmountError):
            validate_amount(0)

    def test_non_numeric_amount_raises_error(self):
        """Non-numeric amounts should raise InvalidAmountError."""
        from app.services.economy_service import validate_amount
        with pytest.raises(InvalidAmountError):
            validate_amount("not a number")


class TestPointsOperations:
    """Test points balance operations."""

    def test_add_points_increases_balance(self, test_user):
        """Adding points should increase the balance."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_points(100)
        assert balance.get_points() == 100

    def test_deduct_points_with_sufficient_balance(self, test_user):
        """Deducting points with sufficient balance should succeed."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_points(100)
        balance.deduct_points(50)
        assert balance.get_points() == 50

    def test_deduct_points_exact_balance(self, test_user):
        """Deducting points equal to balance should leave 0."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_points(100)
        balance.deduct_points(100)
        assert balance.get_points() == 0

    def test_deduct_points_more_than_balance_raises_error(self, test_user):
        """Deducting more points than available should raise error."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_points(100)
        with pytest.raises(InsufficientBalanceError):
            balance.deduct_points(150)
        # Balance should remain unchanged
        assert balance.get_points() == 100

    def test_deduct_points_from_zero_balance_raises_error(self, test_user):
        """Deducting points from zero balance should raise error."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        with pytest.raises(InsufficientBalanceError):
            balance.deduct_points(1)
        assert balance.get_points() == 0

    def test_deduct_invalid_points_raises_error(self, test_user):
        """Deducting invalid amounts should raise error."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_points(100)
        with pytest.raises(InvalidAmountError):
            balance.deduct_points(-10)
        with pytest.raises(InvalidAmountError):
            balance.deduct_points(0)


class TestCurrencyOperations:
    """Test currency balance operations."""

    def test_add_currency_increases_balance(self, test_user):
        """Adding currency should increase the balance."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_currency(200)
        assert balance.get_currency() == 200

    def test_deduct_currency_with_sufficient_balance(self, test_user):
        """Deducting currency with sufficient balance should succeed."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_currency(200)
        balance.deduct_currency(75)
        assert balance.get_currency() == 125

    def test_deduct_currency_exact_balance(self, test_user):
        """Deducting currency equal to balance should leave 0."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_currency(200)
        balance.deduct_currency(200)
        assert balance.get_currency() == 0

    def test_deduct_currency_more_than_balance_raises_error(self, test_user):
        """Deducting more currency than available should raise error."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_currency(100)
        with pytest.raises(InsufficientBalanceError):
            balance.deduct_currency(150)
        # Balance should remain unchanged
        assert balance.get_currency() == 100

    def test_deduct_currency_from_zero_balance_raises_error(self, test_user):
        """Deducting currency from zero balance should raise error."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        with pytest.raises(InsufficientBalanceError):
            balance.deduct_currency(1)
        assert balance.get_currency() == 0


class TestInventoryOperations:
    """Test inventory item operations."""

    def test_add_inventory_item_creates_item(self, test_user):
        """Adding inventory item should create it with correct quantity."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_inventory_item("sword", 5)
        assert balance.get_inventory_quantity("sword") == 5

    def test_add_inventory_item_accumulates(self, test_user):
        """Adding to existing inventory item should accumulate."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_inventory_item("potion", 3)
        balance.add_inventory_item("potion", 2)
        assert balance.get_inventory_quantity("potion") == 5

    def test_deduct_inventory_item_with_sufficient_quantity(self, test_user):
        """Deducting inventory with sufficient quantity should succeed."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_inventory_item("shield", 10)
        balance.deduct_inventory_item("shield", 3)
        assert balance.get_inventory_quantity("shield") == 7

    def test_deduct_inventory_item_exact_quantity(self, test_user):
        """Deducting inventory equal to quantity should leave 0."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_inventory_item("key", 5)
        balance.deduct_inventory_item("key", 5)
        assert balance.get_inventory_quantity("key") == 0

    def test_deduct_inventory_item_more_than_available_raises_error(self, test_user):
        """Deducting more inventory than available should raise error."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_inventory_item("artifact", 5)
        with pytest.raises(InsufficientBalanceError):
            balance.deduct_inventory_item("artifact", 10)
        # Quantity should remain unchanged
        assert balance.get_inventory_quantity("artifact") == 5

    def test_deduct_inventory_item_nonexistent_raises_error(self, test_user):
        """Deducting nonexistent inventory item should raise error."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        with pytest.raises(InsufficientBalanceError):
            balance.deduct_inventory_item("nonexistent", 1)


class TestResourceOperations:
    """Test resource operations."""

    def test_add_resource_creates_resource(self, test_user):
        """Adding resource should create it with correct quantity."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_resource("wood", 50)
        assert balance.get_resource_quantity("wood") == 50

    def test_add_resource_accumulates(self, test_user):
        """Adding to existing resource should accumulate."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_resource("stone", 25)
        balance.add_resource("stone", 15)
        assert balance.get_resource_quantity("stone") == 40

    def test_deduct_resource_with_sufficient_quantity(self, test_user):
        """Deducting resource with sufficient quantity should succeed."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_resource("iron", 100)
        balance.deduct_resource("iron", 40)
        assert balance.get_resource_quantity("iron") == 60

    def test_deduct_resource_exact_quantity(self, test_user):
        """Deducting resource equal to quantity should leave 0."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_resource("copper", 30)
        balance.deduct_resource("copper", 30)
        assert balance.get_resource_quantity("copper") == 0

    def test_deduct_resource_more_than_available_raises_error(self, test_user):
        """Deducting more resource than available should raise error."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_resource("gold", 50)
        with pytest.raises(InsufficientBalanceError):
            balance.deduct_resource("gold", 100)
        # Quantity should remain unchanged
        assert balance.get_resource_quantity("gold") == 50

    def test_deduct_resource_nonexistent_raises_error(self, test_user):
        """Deducting nonexistent resource should raise error."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        with pytest.raises(InsufficientBalanceError):
            balance.deduct_resource("unknown", 1)


class TestScenarios:
    """Test realistic game economy scenarios."""

    def test_scenario_user_with_100_points_deduct_150_fails(self, test_user):
        """User has 100 points, try to deduct 150 -> fails."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_points(100)

        with pytest.raises(InsufficientBalanceError) as exc_info:
            balance.deduct_points(150)

        assert "Insufficient points" in str(exc_info.value)
        assert balance.get_points() == 100

    def test_scenario_user_with_100_points_deduct_100_succeeds(self, test_user):
        """User has 100 points, deduct 100 -> succeeds."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_points(100)

        balance.deduct_points(100)

        assert balance.get_points() == 0

    def test_scenario_user_with_0_points_deduct_1_fails(self, test_user):
        """User has 0 points, deduct 1 -> fails."""
        user, _ = test_user
        balance = get_player_balance(user.id)

        with pytest.raises(InsufficientBalanceError) as exc_info:
            balance.deduct_points(1)

        assert "Insufficient points" in str(exc_info.value)
        assert balance.get_points() == 0

    def test_complex_transaction_sequence(self, test_user):
        """Test complex sequence of transactions across multiple balance types."""
        user, _ = test_user
        balance = get_player_balance(user.id)

        # Build up various balances
        balance.add_points(500)
        balance.add_currency(1000)
        balance.add_inventory_item("sword", 2)
        balance.add_inventory_item("shield", 1)
        balance.add_resource("wood", 100)
        balance.add_resource("stone", 50)

        # Perform various deductions
        balance.deduct_points(100)
        balance.deduct_currency(200)
        balance.deduct_inventory_item("sword", 1)
        balance.deduct_resource("wood", 30)

        # Verify final state
        assert balance.get_points() == 400
        assert balance.get_currency() == 800
        assert balance.get_inventory_quantity("sword") == 1
        assert balance.get_inventory_quantity("shield") == 1
        assert balance.get_resource_quantity("wood") == 70
        assert balance.get_resource_quantity("stone") == 50

    def test_get_all_balances_returns_complete_state(self, test_user):
        """get_all_balances should return complete balance snapshot."""
        user, _ = test_user
        balance = get_player_balance(user.id)

        balance.add_points(100)
        balance.add_currency(200)
        balance.add_inventory_item("item1", 5)
        balance.add_resource("res1", 10)

        all_balances = balance.get_all_balances()

        assert all_balances["user_id"] == user.id
        assert all_balances["points"] == 100
        assert all_balances["currency"] == 200
        assert all_balances["inventory"]["item1"] == 5
        assert all_balances["resources"]["res1"] == 10


class TestErrorMessages:
    """Test error message clarity."""

    def test_insufficient_points_error_message(self, test_user):
        """Error message for insufficient points should be clear."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_points(100)

        try:
            balance.deduct_points(150)
            pytest.fail("Should have raised InsufficientBalanceError")
        except InsufficientBalanceError as e:
            msg = str(e)
            assert "100" in msg
            assert "150" in msg

    def test_insufficient_inventory_error_message(self, test_user):
        """Error message for insufficient inventory should include item ID."""
        user, _ = test_user
        balance = get_player_balance(user.id)
        balance.add_inventory_item("sword", 5)

        try:
            balance.deduct_inventory_item("sword", 10)
            pytest.fail("Should have raised InsufficientBalanceError")
        except InsufficientBalanceError as e:
            msg = str(e)
            assert "sword" in msg
            assert "5" in msg
            assert "10" in msg
