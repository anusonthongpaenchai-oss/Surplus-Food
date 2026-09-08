import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import MealsPage from "../src/pages/MealsPage";

// Fixtures

const MEAL_BIRIYANI = {
  id: "meal_1",
  store_id: "store_1",
  name: "Surplus Biriyani Bowl",
  description: "Flavourful rice dish",
  original_price: 180,
  discounted_price: 79,
  stock_available: 10,
  is_published: true,
};

const MEAL_CHICKEN = {
  id: "meal_2",
  store_id: "store_1",
  name: "Chicken Rice Box",
  description: "Classic Thai chicken rice",
  original_price: 120,
  discounted_price: 55,
  stock_available: 5,
  is_published: true,
};

// Mock global fetch so tests never hit the real API

function mockFetch(meals: typeof MEAL_BIRIYANI[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => meals,
    })
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

// Test cases

describe("FE-1 — MealsPage 'You pay' price", () => {
  it("test_pay_shows_discounted_price — .pay element renders discounted_price, not original_price", async () => {
    mockFetch([MEAL_BIRIYANI]);
    render(<MealsPage />);

    // Wait for async load() to resolve
    const payEl = await screen.findByText("฿79");
    expect(payEl).toBeInTheDocument();
    expect(payEl).toHaveClass("pay");
  });

  it("test_strike_shows_original_price — struck-through element renders original_price", async () => {
    mockFetch([MEAL_BIRIYANI]);
    render(<MealsPage />);

    const strikeEl = await screen.findByText("฿180");
    expect(strikeEl).toBeInTheDocument();
    expect(strikeEl).toHaveClass("strike");
  });

  it("test_pay_and_strike_never_equal — pay price is lower than struck-through price", async () => {
    mockFetch([MEAL_BIRIYANI]);
    render(<MealsPage />);

    const payEl = await screen.findByText("฿79");
    const strikeEl = await screen.findByText("฿180");

    const pay = Number(payEl.textContent?.replace("฿", ""));
    const original = Number(strikeEl.textContent?.replace("฿", ""));
    expect(pay).toBeLessThan(original);
  });

  it("test_multiple_meals_all_show_discounted_price — every meal card uses discounted_price", async () => {
    mockFetch([MEAL_BIRIYANI, MEAL_CHICKEN]);
    render(<MealsPage />);

    // Both discounted prices must appear
    await screen.findByText("฿79");
    await screen.findByText("฿55");

    // Neither pay element should show original price
    const payEls = document.querySelectorAll(".pay");
    const payTexts = Array.from(payEls).map((el) => el.textContent);
    expect(payTexts).not.toContain("฿180");
    expect(payTexts).not.toContain("฿120");
  });

  it("test_out_of_stock_button_disabled — Add to cart button is disabled when stock_available < 1", async () => {
    mockFetch([{ ...MEAL_BIRIYANI, stock_available: 0 }]);
    render(<MealsPage />);

    await waitFor(() => {
      const btn = screen.getByRole("button", { name: /add to cart/i });
      expect(btn).toBeDisabled();
    });
  });
});
