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


async def _add_to_cart(
    client: httpx.AsyncClient, meal_id: str = "meal_1", quantity: int = 2
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


# ---------- Test Cases ---------- #


class TestBE1CheckoutSuccess:
    """The primary regression test for BE-1: checkout must not return 500."""

    @pytest.mark.asyncio
    async def test_checkout_returns_201_with_order(self, client: httpx.AsyncClient):
        """
        After adding items to the cart, POST /v1/th/orders should
        return HTTP 201 with a valid order payload.
        """
        await _add_to_cart(client, meal_id="meal_1", quantity=2)

        resp = await _checkout(client)

        assert resp.status_code == 201, (
            f"Expected 201 Created, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert "order" in body
        assert "message" in body
        assert body["message"] == "Order created successfully"
        assert body["order"]["id"].startswith("ord_")


class TestBE1CartEmptyAfterCheckout:
    """After a successful checkout the cart must be cleared."""

    @pytest.mark.asyncio
    async def test_cart_is_empty_after_checkout(self, client: httpx.AsyncClient):
        """
        GET /v1/th/cart after a successful checkout should return
        an empty items list and zero subtotal.
        """
        await _add_to_cart(client, meal_id="meal_1", quantity=2)
        resp = await _checkout(client)
        assert resp.status_code == 201

        cart_resp = await client.get(f"{BASE}/cart")
        cart = cart_resp.json()

        assert cart["items"] == [], "Cart should be empty after checkout"
        assert cart["item_count"] == 0
        assert cart["subtotal"] == 0.0


class TestBE1StockNotDoubleDecremented:
    """
    Stock is reserved at add-to-cart time.  Checkout must NOT decrement
    it a second time.
    """

    @pytest.mark.asyncio
    async def test_stock_stays_the_same_after_checkout(self, client: httpx.AsyncClient):
        """
        meal_1 starts with stock 10.
        After adding quantity 2 → stock should be 8.
        After checkout → stock should still be 8 (no second decrement).
        """
        await _add_to_cart(client, meal_id="meal_1", quantity=2)

        # Stock after add-to-cart
        meals_before = (await client.get(f"{BASE}/meals")).json()
        meal_1_before = next(m for m in meals_before if m["id"] == "meal_1")
        assert meal_1_before["stock_available"] == 8, (
            "Stock should be 8 after reserving 2 units via add-to-cart"
        )

        # Checkout
        resp = await _checkout(client)
        assert resp.status_code == 201

        # Stock after checkout — must NOT have decreased further
        meals_after = (await client.get(f"{BASE}/meals")).json()
        meal_1_after = next(m for m in meals_after if m["id"] == "meal_1")
        assert meal_1_after["stock_available"] == 8, (
            "Stock should remain 8 after checkout (no double-decrement)"
        )


class TestBE1EmptyCartCheckout:
    """Attempting to checkout with an empty cart should return 400."""

    @pytest.mark.asyncio
    async def test_checkout_empty_cart_returns_400(self, client: httpx.AsyncClient):
        """
        POST /v1/th/orders without any items in the cart should
        return HTTP 400 with an appropriate error detail.
        """
        resp = await _checkout(client)

        assert resp.status_code == 400, (
            f"Expected 400 Bad Request, got {resp.status_code}: {resp.text}"
        )
        body = resp.json()
        assert "detail" in body
        assert "empty" in body["detail"].lower()


class TestBE1OrderStatusConfirmed:
    """A newly created order should have status CONFIRMED."""

    @pytest.mark.asyncio
    async def test_order_status_is_confirmed(self, client: httpx.AsyncClient):
        """
        After checkout, the returned order's status field must be
        'CONFIRMED' (not PENDING or any other state).
        """
        await _add_to_cart(client, meal_id="meal_2", quantity=1)

        resp = await _checkout(client)
        assert resp.status_code == 201

        order = resp.json()["order"]
        assert order["status"] == "CONFIRMED", (
            f"Expected CONFIRMED, got {order['status']}"
        )


class TestBE1OrderLinesMatchCart:
    """Order lines should faithfully reflect what was in the cart."""

    @pytest.mark.asyncio
    async def test_order_lines_match_cart_items(self, client: httpx.AsyncClient):
        """
        Add meal_1 x2 and meal_2 x1, then checkout.
        The order should contain exactly those two lines with correct
        meal_id and quantity values.
        """
        await _add_to_cart(client, meal_id="meal_1", quantity=2)
        await _add_to_cart(client, meal_id="meal_2", quantity=1)

        resp = await _checkout(client)
        assert resp.status_code == 201

        lines = resp.json()["order"]["lines"]
        lines_by_meal = {line["meal_id"]: line for line in lines}

        assert len(lines) == 2, f"Expected 2 order lines, got {len(lines)}"

        assert "meal_1" in lines_by_meal
        assert lines_by_meal["meal_1"]["quantity"] == 2
        assert lines_by_meal["meal_1"]["meal_name"] == "Surplus Biriyani Bowl"

        assert "meal_2" in lines_by_meal
        assert lines_by_meal["meal_2"]["quantity"] == 1
        assert lines_by_meal["meal_2"]["meal_name"] == "Chicken Rice Box"
