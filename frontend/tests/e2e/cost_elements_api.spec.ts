import { test, expect } from "@playwright/test";

/**
 * Isolated API tests for Cost Element dependencies
 * Tests the API calls that CostElementModal makes
 */

test.describe("Cost Element API Dependencies", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');
    await expect(page.getByRole("menuitem", { name: "Dashboard" })).toBeVisible(
      {
        timeout: 30000,
      }
    );
  });

  test("should fetch cost element types with pagination", async ({
    page,
    request,
  }) => {
    // Get auth token
    const authStorage = await page.evaluate(() =>
      localStorage.getItem("auth-storage")
    );
    const token = JSON.parse(authStorage!).state.token;

    // Test the API endpoint that CostElementModal uses
    const response = await request.get(
      "http://localhost:8020/api/v1/cost-element-types?page=1&per_page=100&sort_order=asc",
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    console.log(
      "Cost Element Types API Response:",
      JSON.stringify(data, null, 2)
    );

    // Verify paginated response structure
    expect(data).toHaveProperty("items");
    expect(data).toHaveProperty("total");
    expect(data).toHaveProperty("page");
    expect(data).toHaveProperty("per_page");
    expect(Array.isArray(data.items)).toBe(true);
    expect(data.items.length).toBeGreaterThan(0);

    // Verify first item has required fields
    if (data.items.length > 0) {
      const firstType = data.items[0];
      expect(firstType).toHaveProperty("cost_element_type_id");
      expect(firstType).toHaveProperty("code");
      expect(firstType).toHaveProperty("name");
      console.log(`First type: ${firstType.code} - ${firstType.name}`);
    }
  });

  test("should fetch WBEs with pagination", async ({ page, request }) => {
    // Get auth token
    const authStorage = await page.evaluate(() =>
      localStorage.getItem("auth-storage")
    );
    const token = JSON.parse(authStorage!).state.token;

    // Test the API endpoint that CostElementModal uses
    const response = await request.get(
      "http://localhost:8020/api/v1/wbes?page=1&per_page=100&branch=main&sort_order=asc",
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    console.log("WBEs API Response structure:", {
      hasItems: "items" in data,
      hasTotal: "total" in data,
      isArray: Array.isArray(data),
      keys: Object.keys(data),
    });

    // WBEs might return array or paginated response depending on filters
    if (Array.isArray(data)) {
      console.log(`WBEs returned as array with ${data.length} items`);
    } else {
      expect(data).toHaveProperty("items");
      expect(data).toHaveProperty("total");
      console.log(
        `WBEs returned as paginated response with ${data.items.length} items`
      );
    }
  });
});
