"""Game economy service for managing player balances and resources.

Handles all balance operations (points, currency, inventory, resources) with
validation to prevent negative balances/quantities.
"""
from __future__ import annotations

from typing import Literal

from app.extensions import db
from app.models import User


class EconomyError(ValueError):
    """Base exception for economy-related errors."""
    pass


class InsufficientBalanceError(EconomyError):
    """Raised when attempting to deduct more than available balance."""
    pass


class InvalidAmountError(EconomyError):
    """Raised when an invalid amount is provided."""
    pass


class BalanceType(str):
    """Enumeration of balance types in the game economy."""
    POINTS = "points"
    CURRENCY = "currency"
    INVENTORY = "inventory"
    RESOURCES = "resources"


def validate_amount(amount: int | float) -> None:
    """Validate that an amount is a positive number.

    Args:
        amount: The amount to validate.

    Raises:
        InvalidAmountError: If amount is not positive.
    """
    try:
        amount_num = float(amount)
    except (TypeError, ValueError):
        raise InvalidAmountError(f"Amount must be a number, got {type(amount).__name__}")

    if amount_num <= 0:
        raise InvalidAmountError(f"Amount must be positive, got {amount_num}")


def check_balance_sufficient(
    current_balance: int | float,
    deduction_amount: int | float,
    balance_type: str = "balance",
) -> None:
    """Validate that current balance is sufficient for a deduction.

    Args:
        current_balance: The current balance amount.
        deduction_amount: The amount to deduct.
        balance_type: Description of the balance type (for error messages).

    Raises:
        InsufficientBalanceError: If deduction would result in negative balance.
    """
    if current_balance < deduction_amount:
        raise InsufficientBalanceError(
            f"Insufficient {balance_type}: have {current_balance}, "
            f"need to deduct {deduction_amount}"
        )


class PlayerBalance:
    """Manages a player's economy balances.

    This class tracks points, currency, inventory items, and resources
    with built-in validation to prevent negative values.
    """

    def __init__(self, user_id: int):
        """Initialize a player balance manager.

        Args:
            user_id: The user ID to manage balances for.
        """
        self.user_id = user_id
        self.user = self._get_user()
        # Initialize balance storage (in a real implementation,
        # these would be database columns or a separate table)
        self._balances = {
            BalanceType.POINTS: 0,
            BalanceType.CURRENCY: 0,
            BalanceType.INVENTORY: {},
            BalanceType.RESOURCES: {},
        }

    def _get_user(self) -> User:
        """Get the user from the database.

        Returns:
            The User model instance.

        Raises:
            EconomyError: If user is not found.
        """
        user = db.session.get(User, self.user_id)
        if user is None:
            raise EconomyError(f"User {self.user_id} not found")
        return user

    def get_points(self) -> int:
        """Get current points balance.

        Returns:
            Current points balance.
        """
        return self._balances[BalanceType.POINTS]

    def get_currency(self) -> int:
        """Get current currency balance.

        Returns:
            Current currency balance.
        """
        return self._balances[BalanceType.CURRENCY]

    def get_inventory_quantity(self, item_id: str) -> int:
        """Get quantity of an inventory item.

        Args:
            item_id: The inventory item ID.

        Returns:
            Current quantity of the item.
        """
        return self._balances[BalanceType.INVENTORY].get(item_id, 0)

    def get_resource_quantity(self, resource_id: str) -> int:
        """Get quantity of a resource.

        Args:
            resource_id: The resource ID.

        Returns:
            Current quantity of the resource.
        """
        return self._balances[BalanceType.RESOURCES].get(resource_id, 0)

    def add_points(self, amount: int) -> None:
        """Add points to the balance.

        Args:
            amount: Amount of points to add.

        Raises:
            InvalidAmountError: If amount is not positive.
        """
        validate_amount(amount)
        self._balances[BalanceType.POINTS] += int(amount)

    def deduct_points(self, amount: int) -> None:
        """Deduct points from the balance.

        Args:
            amount: Amount of points to deduct.

        Raises:
            InvalidAmountError: If amount is not positive.
            InsufficientBalanceError: If deduction would result in negative balance.
        """
        validate_amount(amount)
        check_balance_sufficient(
            self._balances[BalanceType.POINTS],
            amount,
            "points",
        )
        self._balances[BalanceType.POINTS] -= int(amount)

    def add_currency(self, amount: int) -> None:
        """Add currency to the balance.

        Args:
            amount: Amount of currency to add.

        Raises:
            InvalidAmountError: If amount is not positive.
        """
        validate_amount(amount)
        self._balances[BalanceType.CURRENCY] += int(amount)

    def deduct_currency(self, amount: int) -> None:
        """Deduct currency from the balance.

        Args:
            amount: Amount of currency to deduct.

        Raises:
            InvalidAmountError: If amount is not positive.
            InsufficientBalanceError: If deduction would result in negative balance.
        """
        validate_amount(amount)
        check_balance_sufficient(
            self._balances[BalanceType.CURRENCY],
            amount,
            "currency",
        )
        self._balances[BalanceType.CURRENCY] -= int(amount)

    def add_inventory_item(self, item_id: str, quantity: int) -> None:
        """Add items to inventory.

        Args:
            item_id: The inventory item ID.
            quantity: Quantity to add.

        Raises:
            InvalidAmountError: If quantity is not positive.
        """
        validate_amount(quantity)
        if item_id not in self._balances[BalanceType.INVENTORY]:
            self._balances[BalanceType.INVENTORY][item_id] = 0
        self._balances[BalanceType.INVENTORY][item_id] += int(quantity)

    def deduct_inventory_item(self, item_id: str, quantity: int) -> None:
        """Deduct items from inventory.

        Args:
            item_id: The inventory item ID.
            quantity: Quantity to deduct.

        Raises:
            InvalidAmountError: If quantity is not positive.
            InsufficientBalanceError: If deduction would result in negative quantity.
        """
        validate_amount(quantity)
        current = self._balances[BalanceType.INVENTORY].get(item_id, 0)
        check_balance_sufficient(
            current,
            quantity,
            f"inventory item {item_id}",
        )
        self._balances[BalanceType.INVENTORY][item_id] = current - int(quantity)

    def add_resource(self, resource_id: str, quantity: int) -> None:
        """Add resources.

        Args:
            resource_id: The resource ID.
            quantity: Quantity to add.

        Raises:
            InvalidAmountError: If quantity is not positive.
        """
        validate_amount(quantity)
        if resource_id not in self._balances[BalanceType.RESOURCES]:
            self._balances[BalanceType.RESOURCES][resource_id] = 0
        self._balances[BalanceType.RESOURCES][resource_id] += int(quantity)

    def deduct_resource(self, resource_id: str, quantity: int) -> None:
        """Deduct resources.

        Args:
            resource_id: The resource ID.
            quantity: Quantity to deduct.

        Raises:
            InvalidAmountError: If quantity is not positive.
            InsufficientBalanceError: If deduction would result in negative quantity.
        """
        validate_amount(quantity)
        current = self._balances[BalanceType.RESOURCES].get(resource_id, 0)
        check_balance_sufficient(
            current,
            quantity,
            f"resource {resource_id}",
        )
        self._balances[BalanceType.RESOURCES][resource_id] = current - int(quantity)

    def get_all_balances(self) -> dict:
        """Get all balances for the player.

        Returns:
            Dictionary containing all balance information.
        """
        return {
            "user_id": self.user_id,
            "points": self._balances[BalanceType.POINTS],
            "currency": self._balances[BalanceType.CURRENCY],
            "inventory": self._balances[BalanceType.INVENTORY].copy(),
            "resources": self._balances[BalanceType.RESOURCES].copy(),
        }


def get_player_balance(user_id: int) -> PlayerBalance:
    """Get or create a player balance manager.

    Args:
        user_id: The user ID to manage balances for.

    Returns:
        PlayerBalance instance for the user.

    Raises:
        EconomyError: If user is not found.
    """
    return PlayerBalance(user_id)
