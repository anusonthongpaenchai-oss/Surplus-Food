import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import StockEventsPage from "../src/pages/StockEventsPage";

// Fixtures

const EVENT_MEAL_1 = {
  id: "evt_1",
  meal_id: "meal_1",
  store_id: "store_1",
  event_type: "DECREMENT",
  event_source: "USER",
  quantity: 1,
  stock_before: 10,
  stock_after: 9,
  reference_id: null,
  note: "Cart reserve",
  created_at: "2025-01-01T10:00:00Z",
};

const EVENT_MEAL_2 = {
  id: "evt_2",
  meal_id: "meal_2",
  store_id: "store_1",
  event_type: "DECREMENT",
  event_source: "USER",
  quantity: 3,
  stock_before: 5,
  stock_after: 2,
  reference_id: null,
  note: "Cart reserve",
  created_at: "2025-01-01T11:00:00Z",
};

// Mock global fetch

function mockFetch(responsesByUrl: Record<string, object[]>) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      const matched = Object.entries(responsesByUrl).find(([key]) =>
        url.includes(key)
      );
      const body = matched ? matched[1] : [];
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => body,
      });
    })
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

// Test cases

describe("FE-2 — Stock events filter", () => {
  it("test_initial_load_fetches_all_events — page loads without filter and shows all events", async () => {
    mockFetch({ "/stock-events": [EVENT_MEAL_1, EVENT_MEAL_2] });
    render(<StockEventsPage />);

    await screen.findByText("meal_1");
    await screen.findByText("meal_2");
  });

  it("test_apply_filter_sends_meal_id_param — clicking Apply filter sends ?meal_id= (not ?meal=)", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [EVENT_MEAL_1],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<StockEventsPage />);
    await screen.findByText("meal_1"); // wait for initial load

    const input = screen.getByPlaceholderText(/filter by meal_id/i);
    await userEvent.clear(input);
    await userEvent.type(input, "meal_1");

    const applyBtn = screen.getByRole("button", { name: /apply filter/i });
    await userEvent.click(applyBtn);

    // The second fetch (after clicking Apply) must use ?meal_id=
    const urls: string[] = fetchMock.mock.calls.map((c) => c[0] as string);
    const filterCall = urls.find((u) => u.includes("meal_1"));
    expect(filterCall).toBeDefined();
    expect(filterCall).toMatch(/[?&]meal_id=/);      // ✅ correct param name
    expect(filterCall).not.toMatch(/[?&]meal=[^_]/); // ❌ old broken param
  });

  it("test_filtered_results_shown_in_table — only matching meal_id rows are rendered", async () => {
    mockFetch({
      "stock-events?meal_id=meal_2": [EVENT_MEAL_2],
      "stock-events": [EVENT_MEAL_1, EVENT_MEAL_2],
    });
    render(<StockEventsPage />);
    await screen.findByText("meal_1"); // initial load done

    const input = screen.getByPlaceholderText(/filter by meal_id/i);
    await userEvent.clear(input);
    await userEvent.type(input, "meal_2");
    await userEvent.click(screen.getByRole("button", { name: /apply filter/i }));

    await waitFor(() => {
      expect(screen.queryByText("meal_1")).not.toBeInTheDocument();
      expect(screen.getByText("meal_2")).toBeInTheDocument();
    });
  });

  it("test_clear_resets_filter_and_reloads — clicking Clear resets input and reloads all events", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [EVENT_MEAL_1, EVENT_MEAL_2],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<StockEventsPage />);
    await screen.findByText("meal_1");

    // Type a filter then clear it
    const input = screen.getByPlaceholderText(/filter by meal_id/i);
    await userEvent.type(input, "meal_1");
    await userEvent.click(screen.getByRole("button", { name: /clear/i }));

    // Input must be empty
    expect(input).toHaveValue("");

    // A new fetch (no filter) must be triggered — url must NOT include meal_id param
    await waitFor(() => {
      const urls: string[] = fetchMock.mock.calls.map((c) => c[0] as string);
      const lastUrl = urls[urls.length - 1];
      expect(lastUrl).not.toMatch(/[?&]meal_id=/);
    });
  });

  it("test_empty_filter_does_not_send_param — submitting empty input omits meal_id from query", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<StockEventsPage />);

    const applyBtn = screen.getByRole("button", { name: /apply filter/i });
    await userEvent.click(applyBtn);

    await waitFor(() => {
      const urls: string[] = fetchMock.mock.calls.map((c) => c[0] as string);
      const lastUrl = urls[urls.length - 1];
      expect(lastUrl).not.toMatch(/[?&]meal_id=/);
    });
  });
});
