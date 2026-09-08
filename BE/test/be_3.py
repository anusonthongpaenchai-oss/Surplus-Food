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
    client: httpx.AsyncClient, meal_id: str = "meal_2", quantity: int = 3
):
    """Helper — add an item to the cart and return the response."""
    resp = await client.post(
        f"{BASE}/cart/items",
        json={"meal_id": meal_id, "quantity": quantity},
    )
    assert resp.status_code == 200, f"Add-to-cart failed: {resp.text}"
    return resp


async def _checkout(client: httpx.AsyncClient):
    """Helper — place an order (checkout) and return the raw response."""
    return await client.post(f"{BASE}/orders")


async def _cancel_order(client: httpx.AsyncClient, order_id: str):
    """Helper — cancel an order by ID and return the raw response."""
    return await client.post(f"{BASE}/orders/{order_id}/cancel")


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


class TestBE3CancelRestoresStock:
    """
    Primary regression for BE-3:
    Cancel must restore exactly line.quantity units back to the meal — not a hardcoded value.
    Scenario from README: add meal_2 qty 3 -> place order -> cancel -> stock back to 5.
    """

    @pytest.mark.asyncio
    async def test_stock_restored_to_initial_after_cancel(self, client: httpx.AsyncClient):
        """
        meal_2 starts at stock 5.
        Add qty 3 -> stock becomes 2.
        Place order -> stock remains 2.
        Cancel order -> stock must return to 5 (restore exactly 3 units).
        """
        meal_id = "meal_2"
        quantity = 3

        # Verify initial stock
        initial_stock = await _get_stock(client, meal_id)
        assert initial_stock == 5, f"Expected initial stock=5, got {initial_stock}"

        # Add to cart — stock decremented at reservation
        await _add_to_cart(client, meal_id=meal_id, quantity=quantity)
        stock_after_cart = await _get_stock(client, meal_id)
        assert stock_after_cart == 2, (
            f"Expected stock=2 after reserving {quantity} units, got {stock_after_cart}"
        )

        # Place order — stock must NOT decrement again
        resp = await _checkout(client)
        assert resp.status_code == 201, f"Checkout failed: {resp.text}"
        order_id = resp.json()["order"]["id"]

        stock_after_order = await _get_stock(client, meal_id)
        assert stock_after_order == 2, (
            "Stock should remain 2 after checkout (no double-decrement)"
        )

        # Cancel order — stock must be fully restored
        cancel_resp = await _cancel_order(client, order_id)
        assert cancel_resp.status_code == 200, f"Cancel failed: {cancel_resp.text}"

        stock_after_cancel = await _get_stock(client, meal_id)
        assert stock_after_cancel == initial_stock, (
            f"Expected stock={initial_stock} after cancel, got {stock_after_cancel}. "
            f"Bug: quantity was not restored correctly (was hardcoded as 3 instead of line.quantity)"
        )


class TestBE3CancelOrderStatus:
    """Order status must be CANCELLED after a successful cancel."""

    @pytest.mark.asyncio
    async def test_order_status_is_cancelled(self, client: httpx.AsyncClient):
        """
        After cancelling an order, the returned order object's status
        must be 'CANCELLED'.
        """
        await _add_to_cart(client, meal_id="meal_2", quantity=3)

        resp = await _checkout(client)
        assert resp.status_code == 201
        order_id = resp.json()["order"]["id"]

        cancel_resp = await _cancel_order(client, order_id)
        assert cancel_resp.status_code == 200, f"Cancel failed: {cancel_resp.text}"

        order = cancel_resp.json()
        assert order["status"] == "CANCELLED", (
            f"Expected status=CANCELLED, got {order['status']}"
        )


class TestBE3CancelStockEvent:
    """Cancelling an order must produce an INCREMENT stock event for audit trail."""

    @pytest.mark.asyncio
    async def test_cancel_creates_increment_stock_event(self, client: httpx.AsyncClient):
        """
        After cancellation, the stock-events log must contain at least one
        INCREMENT event for the cancelled meal, confirming the stock restoration
        is tracked in the audit trail.
        """
        meal_id = "meal_2"
        quantity = 3

        await _add_to_cart(client, meal_id=meal_id, quantity=quantity)

        resp = await _checkout(client)
        assert resp.status_code == 201
        order_id = resp.json()["order"]["id"]

        await _cancel_order(client, order_id)

        events = await _get_stock_events(client)
        cancel_events = [
            e for e in events
            if e["meal_id"] == meal_id
            and e["event_type"] == "INCREMENT"
            and e["reference_id"] == order_id
        ]

        assert len(cancel_events) >= 1, (
            f"Expected at least 1 INCREMENT stock event for {meal_id} after cancel, "
            f"got {len(cancel_events)}. Events: {events}"
        )
        assert cancel_events[0]["quantity"] == quantity, (
            f"INCREMENT event quantity should be {quantity}, "
            f"got {cancel_events[0]['quantity']}"
        )


class TestBE3MultiItemCancelRestoresAllStock:
    """
    Cancelling an order with multiple meal lines must restore stock
    for every line — not just the first one.
    """

    @pytest.mark.asyncio
    async def test_multi_item_cancel_restores_all_meals_stock(self, client: httpx.AsyncClient):
        """
        Add meal_1 qty 2 and meal_2 qty 3, then place and cancel the order.
        Both meals must have their stock fully restored to initial values.
        """
        items = [
            ("meal_1", 2),
            ("meal_2", 3),
        ]

        # Capture initial stock for each meal
        initial_stocks = {}
        for meal_id, _ in items:
            initial_stocks[meal_id] = await _get_stock(client, meal_id)

        # Add items to cart
        for meal_id, quantity in items:
            await _add_to_cart(client, meal_id=meal_id, quantity=quantity)

        # Place order
        resp = await _checkout(client)
        assert resp.status_code == 201, f"Checkout failed: {resp.text}"
        order_id = resp.json()["order"]["id"]

        # Cancel order
        cancel_resp = await _cancel_order(client, order_id)
        assert cancel_resp.status_code == 200, f"Cancel failed: {cancel_resp.text}"

        # Verify stock restored for all meals
        for meal_id, quantity in items:
            stock_after = await _get_stock(client, meal_id)
            assert stock_after == initial_stocks[meal_id], (
                f"{meal_id}: expected stock={initial_stocks[meal_id]} after cancel, "
                f"got {stock_after} (quantity {quantity} was not restored)"
            )


class TestBE3CancelEdgeCases:
    """Edge cases: cancelling an already-cancelled or non-existent order must fail."""

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_order_returns_400(self, client: httpx.AsyncClient):
        """
        Cancelling an order that is already CANCELLED must return 400.
        Stock must not be double-restored.
        """
        meal_id = "meal_2"
        quantity = 3

        await _add_to_cart(client, meal_id=meal_id, quantity=quantity)
        resp = await _checkout(client)
        assert resp.status_code == 201
        order_id = resp.json()["order"]["id"]

        # First cancel — should succeed
        first_cancel = await _cancel_order(client, order_id)
        assert first_cancel.status_code == 200

        stock_after_first = await _get_stock(client, meal_id)

        # Second cancel — should fail with 400
        second_cancel = await _cancel_order(client, order_id)
        assert second_cancel.status_code == 400, (
            f"Expected 400 on double-cancel, got {second_cancel.status_code}"
        )

        # Stock must NOT be incremented again
        stock_after_second = await _get_stock(client, meal_id)
        assert stock_after_second == stock_after_first, (
            f"Stock should not change on rejected double-cancel. "
            f"Before={stock_after_first}, After={stock_after_second}"
        )

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order_returns_404(self, client: httpx.AsyncClient):
        """
        Cancelling an order ID that does not exist must return 404.
        """
        resp = await _cancel_order(client, "ord_nonexistent")
        assert resp.status_code == 404, (
            f"Expected 404 for unknown order, got {resp.status_code}"
        )
