import { test, expect } from "@playwright/test";

test.describe("Time Machine Component", () => {
  test.beforeEach(async ({ page }) => {
    // Login with seeded admin account
    await page.goto("/login");
    await page.fill('input[name="email"]', "admin@backcast.org");
    await page.fill('input[name="password"]', "admin123");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
  });

  test("Time Machine appears when viewing a project", async ({ page }) => {
    // Navigate to projects list
    await page.goto("/projects");
    await page.waitForSelector(".ant-table-row");

    // Click on first project
    await page.click(".ant-table-row:first-child");
    await page.waitForURL(/\/projects\/[a-f0-9-]+$/);

    // Verify Time Machine compact button is visible
    const timeMachineButton = page
      .locator('button:has-text("Jan"), button:has-text("Now")')
      .first();
    await expect(timeMachineButton).toBeVisible();

    // Verify branch indicator is visible
    const branchTag = page.locator('.ant-tag:has-text("main")');
    await expect(branchTag).toBeVisible();
  });

  test("Time Machine can be expanded and collapsed", async ({ page }) => {
    // Navigate to a project
    await page.goto("/projects");
    await page.waitForSelector(".ant-table-row");
    await page.click(".ant-table-row:first-child");
    await page.waitForURL(/\/projects\/[a-f0-9-]+$/);

    // Click to expand Time Machine
    const timeMachineButton = page
      .locator('button:has-text("Jan"), button:has-text("Now")')
      .first();
    await timeMachineButton.click();

    // Verify expanded panel is visible
    await expect(page.locator(".ant-slider")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=Branch")).toBeVisible();

    // Click to collapse
    await timeMachineButton.click();

    // Verify panel is hidden
    await expect(page.locator(".ant-slider")).not.toBeVisible();
  });

  test("Time Machine timeline slider is functional", async ({ page }) => {
    // Navigate to a project
    await page.goto("/projects");
    await page.waitForSelector(".ant-table-row");
    await page.click(".ant-table-row:first-child");
    await page.waitForURL(/\/projects\/[a-f0-9-]+$/);

    // Expand Time Machine
    const timeMachineButton = page
      .locator('button:has-text("Jan"), button:has-text("Now")')
      .first();
    await timeMachineButton.click();

    // Wait for slider to be visible
    const slider = page.locator(".ant-slider");
    await expect(slider).toBeVisible({ timeout: 5000 });

    // Verify slider has marks (start and end dates)
    const sliderMarks = page.locator(".ant-slider-mark-text");
    await expect(sliderMarks).toHaveCount(2, { timeout: 5000 }); // Start and end date
  });

  test("Quick jump buttons work", async ({ page }) => {
    // Navigate to a project
    await page.goto("/projects");
    await page.waitForSelector(".ant-table-row");
    await page.click(".ant-table-row:first-child");
    await page.waitForURL(/\/projects\/[a-f0-9-]+$/);

    // Expand Time Machine
    const timeMachineButton = page
      .locator('button:has-text("Jan"), button:has-text("Now")')
      .first();
    await timeMachineButton.click();

    // Wait for quick jump buttons
    await expect(page.locator('button:has-text("1D")')).toBeVisible({
      timeout: 5000,
    });

    // Click "1W" button
    await page.click('button:has-text("1W")');

    // Verify the compact button shows a historical date (not "Now")
    await expect(timeMachineButton).not.toContainText("Now");
  });

  test("Reset to Now button works", async ({ page }) => {
    // Navigate to a project
    await page.goto("/projects");
    await page.waitForSelector(".ant-table-row");
    await page.click(".ant-table-row:first-child");
    await page.waitForURL(/\/projects\/[a-f0-9-]+$/);

    // Expand Time Machine
    const timeMachineButton = page
      .locator('button:has-text("Jan"), button:has-text("Now")')
      .first();
    await timeMachineButton.click();

    // Click a quick jump to go to past
    await page.click('button:has-text("1M")');
    await page.waitForTimeout(500);

    // Verify "Reset to Now" button appears
    const resetButton = page.locator('button:has-text("Reset to Now")');
    await expect(resetButton).toBeVisible();

    // Click reset
    await resetButton.click();
    await page.waitForTimeout(500);

    // Verify compact button shows "Now" again
    await expect(timeMachineButton).toContainText("Now");

    // Verify reset button is hidden
    await expect(resetButton).not.toBeVisible();
  });

  test("Date picker allows precise time selection", async ({ page }) => {
    // Navigate to a project
    await page.goto("/projects");
    await page.waitForSelector(".ant-table-row");
    await page.click(".ant-table-row:first-child");
    await page.waitForURL(/\/projects\/[a-f0-9-]+$/);

    // Expand Time Machine
    const timeMachineButton = page
      .locator('button:has-text("Jan"), button:has-text("Now")')
      .first();
    await timeMachineButton.click();

    // Wait for date picker
    const datePicker = page.locator(".ant-picker");
    await expect(datePicker).toBeVisible({ timeout: 5000 });

    // Click date picker
    await datePicker.click();

    // Verify date picker panel opens
    await expect(page.locator(".ant-picker-dropdown")).toBeVisible({
      timeout: 3000,
    });
  });

  test("Branch selector shows available branches", async ({ page }) => {
    // Navigate to a project
    await page.goto("/projects");
    await page.waitForSelector(".ant-table-row");
    await page.click(".ant-table-row:first-child");
    await page.waitForURL(/\/projects\/[a-f0-9-]+$/);

    // Expand Time Machine
    const timeMachineButton = page
      .locator('button:has-text("Jan"), button:has-text("Now")')
      .first();
    await timeMachineButton.click();

    // Wait for branch selector
    await expect(page.locator("text=Branch")).toBeVisible({ timeout: 5000 });

    // Verify "main" branch is shown
    const branchSelect = page
      .locator(".ant-select")
      .filter({ hasText: "main" });
    await expect(branchSelect).toBeVisible();
  });

  test("Time Machine persists selection across navigation", async ({
    page,
  }) => {
    // Navigate to a project
    await page.goto("/projects");
    await page.waitForSelector(".ant-table-row");
    await page.click(".ant-table-row:first-child");
    const projectUrl = page.url();

    // Expand Time Machine and select a time
    const timeMachineButton = page
      .locator('button:has-text("Jan"), button:has-text("Now")')
      .first();
    await timeMachineButton.click();
    await page.click('button:has-text("1M")');
    await page.waitForTimeout(500);

    // Navigate away
    await page.goto("/projects");
    await page.waitForTimeout(500);

    // Navigate back to the same project
    await page.goto(projectUrl);
    await page.waitForTimeout(500);

    // Verify the selected time is still shown (not "Now")
    await expect(timeMachineButton).not.toContainText("Now");
  });
});
