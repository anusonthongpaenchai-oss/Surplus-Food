import httpx
import pytest
import pytest_asyncio

from app.main import app
from app.repositories.db import db

BASE = "/v1/th"


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the in-memory database before each test."""
    db.reset()
    yield


@pytest_asyncio.fixture()
async def client():
    """Provide an httpx AsyncClient with ASGITransport for FastAPI."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


# ---------- Helpers ---------- #


async def _add_to_cart(
    client: httpx.AsyncClient, meal_id: str = "meal_1", quantity: int = 1
):
    """Helper — add an item to the cart and return the response."""
    resp = await client.post(
        f"{BASE}/cart/items",
        json={"meal_id": meal_id, "quantity": quantity},
    )
    assert resp.status_code == 200, f"Add-to-cart failed: {resp.text}"
    return resp


async def _update_cart_item(
    client: httpx.AsyncClient, meal_id: str, quantity: int
):
    """Helper — update quantity of a cart item and return the raw response."""
    return await client.patch(
        f"{BASE}/cart/items/{meal_id}",
        json={"quantity": quantity},
    )


async def _get_stock(client: httpx.AsyncClient, meal_id: str) -> int:
    """Helper — fetch current stock_available for a given meal."""
    resp = await client.get(f"{BASE}/meals")
    assert resp.status_code == 200, f"GET /meals failed: {resp.text}"
    meal = next(m for m in resp.json() if m["id"] == meal_id)
    return meal["stock_available"]


async def _get_stock_events(client: httpx.AsyncClient) -> list[dict]:
    """Helper — fetch all stock events."""
    resp = await client.get(f"{BASE}/stock-events")
    assert resp.status_code == 200, f"GET /stock-events failed: {resp.text}"
    return resp.json()


# ---------- Test Cases ---------- #


class TestBE4IncreaseQtyDecrementsStock:
    """
    Primary regression for BE-4:
    When a cart item's quantity is increased, the delta must be DECREMENTED
    from stock — not incremented (the original bug).

    README scenario:
      1. Add meal_1 qty 1  → stock becomes 9
      2. Update to qty 3   → stock becomes 7 (delta=2 reserved)
    """

    @pytest.mark.asyncio
    async def test_increase_qty_decrements_stock_by_delta(self, client: httpx.AsyncClient):
        """
        meal_1 starts at stock 10.
        Add qty 1 → stock becomes 9.
        Update to qty 3 → stock must become 7 (delta=2 additional reserve).
        """
        meal_id = "meal_1"

        # Verify initial stock
        initial_stock = await _get_stock(client, meal_id)
        assert initial_stock == 10, f"Expected initial stock=10, got {initial_stock}"

        # Add qty=1 — stock reserved by 1
        await _add_to_cart(client, meal_id=meal_id, quantity=1)
        stock_after_add = await _get_stock(client, meal_id)
        assert stock_after_add == 9, (
            f"Expected stock=9 after adding qty=1, got {stock_after_add}"
        )

        # Update to qty=3 — delta=2, stock must decrement by 2 more
        resp = await _update_cart_item(client, meal_id=meal_id, quantity=3)
        assert resp.status_code == 200, f"Update cart item failed: {resp.text}"

        stock_after_update = await _get_stock(client, meal_id)
        assert stock_after_update == 7, (
            f"Expected stock=7 after updating to qty=3 (delta=2), got {stock_after_update}. "
            f"Bug: INCREMENT was used instead of DECREMENT on cart increase."
        )

    @pytest.mark.asyncio
    async def test_increase_qty_creates_decrement_stock_event(self, client: httpx.AsyncClient):
        """
        Increasing cart quantity must produce a DECREMENT stock event
        with quantity equal to the delta (not the full new quantity).
        """
        meal_id = "meal_1"

        await _add_to_cart(client, meal_id=meal_id, quantity=1)
        resp = await _update_cart_item(client, meal_id=meal_id, quantity=3)
        assert resp.status_code == 200

        events = await _get_stock_events(client)
        # Find DECREMENT events from the cart update (note="reserve on cart increase")
        increase_events = [
            e for e in events
            if e["meal_id"] == meal_id
            and e["event_type"] == "DECREMENT"
            and e.get("note") == "reserve on cart increase"
        ]

        assert len(increase_events) >= 1, (
            f"Expected at least 1 DECREMENT event for cart increase, got {len(increase_events)}. "
            f"All events: {events}"
        )
        assert increase_events[0]["quantity"] == 2, (
            f"DECREMENT event quantity should be delta=2, got {increase_events[0]['quantity']}"
        )


class TestBE4DecreaseQtyReleasesStock:
    """
    When a cart item's quantity is decreased, the delta must be
    INCREMENTED back to stock (releasing reserved units).
    """

    @pytest.mark.asyncio
    async def test_decrease_qty_releases_stock_by_delta(self, client: httpx.AsyncClient):
        """
        Add meal_1 qty=3 → stock=7.
        Update to qty=1 → delta=-2, stock must return to 9.
        """
        meal_id = "meal_1"

        await _add_to_cart(client, meal_id=meal_id, quantity=3)
        stock_after_add = await _get_stock(client, meal_id)
        assert stock_after_add == 7, (
            f"Expected stock=7 after adding qty=3, got {stock_after_add}"
        )

        resp = await _update_cart_item(client, meal_id=meal_id, quantity=1)
        assert resp.status_code == 200, f"Update cart item failed: {resp.text}"

        stock_after_update = await _get_stock(client, meal_id)
        assert stock_after_update == 9, (
            f"Expected stock=9 after decreasing to qty=1 (delta=-2 released), "
            f"got {stock_after_update}"
        )


class TestBE4NoChangeQty:
    """
    When the cart item quantity is updated to the same value,
    no stock event should be triggered.
    """

    @pytest.mark.asyncio
    async def test_same_qty_does_not_change_stock(self, client: httpx.AsyncClient):
        """
        Add meal_1 qty=2 → stock=8.
        Update to qty=2 (no change) → stock must remain 8.
        """
        meal_id = "meal_1"

        await _add_to_cart(client, meal_id=meal_id, quantity=2)
        stock_after_add = await _get_stock(client, meal_id)
        assert stock_after_add == 8, (
            f"Expected stock=8 after adding qty=2, got {stock_after_add}"
        )

        resp = await _update_cart_item(client, meal_id=meal_id, quantity=2)
        assert resp.status_code == 200, f"Update cart item failed: {resp.text}"

        stock_after_update = await _get_stock(client, meal_id)
        assert stock_after_update == 8, (
            f"Expected stock to remain 8 when qty unchanged, got {stock_after_update}"
        )


class TestBE4UpdateItemNotInCart:
    """
    Updating a cart item that does not exist must return 404.
    """

    @pytest.mark.asyncio
    async def test_update_nonexistent_cart_item_returns_404(self, client: httpx.AsyncClient):
        """
        PATCH /v1/th/cart/items/meal_1 without ever adding meal_1 to cart
        must return HTTP 404.
        """
        resp = await _update_cart_item(client, meal_id="meal_1", quantity=3)
        assert resp.status_code == 404, (
            f"Expected 404 for item not in cart, got {resp.status_code}: {resp.text}"
        )
