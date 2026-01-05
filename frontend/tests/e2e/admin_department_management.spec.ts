import { test, expect } from "@playwright/test";

test.describe("Admin Department Management", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[type="email"]', "admin@example.com");
    await page.fill('input[type="password"]', "admin123");
    await page.click('button[type="submit"]');

    // Wait for redirect to home
    await page.waitForURL("/");

    // Navigate to Admin > Department Management
    await page.click("text=Admin");
    await page.click("text=Department Management");
    await page.waitForURL("/admin/departments");
  });

  test("should display department management page with table", async ({
    page,
  }) => {
    // Check page title
    await expect(page.locator("text=Department Management")).toBeVisible();

    // Check table is visible
    await expect(page.locator('[role="table"]')).toBeVisible();

    // Check Add Department button
    await expect(
      page.locator('button:has-text("Add Department")')
    ).toBeVisible();
  });

  test("should create a new department", async ({ page }) => {
    // Click Add Department button
    await page.click('button:has-text("Add Department")');

    // Wait for modal
    await expect(page.locator('[role="dialog"]')).toBeVisible();

    // Fill in department form
    await page.fill('input[placeholder="Engineering"]', "Test Department");
    await page.fill('input[placeholder="ENG"]', "TEST");

    // Optionally fill description
    const descriptionField = page.locator(
      'textarea[placeholder*="description"]'
    );
    if (await descriptionField.isVisible()) {
      await descriptionField.fill("Test department for E2E testing");
    }

    // Submit form
    await page.click('button:has-text("Create")');

    // Wait for success message
    await expect(page.locator("text=Created successfully")).toBeVisible({
      timeout: 10000,
    });

    // Verify department appears in table
    await expect(page.locator("text=Test Department")).toBeVisible();
    await expect(page.locator("text=TEST")).toBeVisible();
  });

  test("should edit an existing department", async ({ page }) => {
    // Find and click edit button for the first department
    const firstEditButton = page
      .locator('button[title="Edit Department"]')
      .first();
    await firstEditButton.click();

    // Wait for modal
    await expect(page.locator('[role="dialog"]')).toBeVisible();

    // Modify the name
    const nameInput = page.locator('input[value*=""]').first();
    await nameInput.clear();
    await nameInput.fill("Updated Department Name");

    // Submit form
    await page.click('button:has-text("Save")');

    // Wait for success message
    await expect(page.locator("text=Updated successfully")).toBeVisible({
      timeout: 10000,
    });
  });

  test("should delete a department with confirmation", async ({ page }) => {
    // Get initial count of rows
    const initialRowCount = await page.locator('[role="row"]').count();

    // Click delete button for first department
    const firstDeleteButton = page
      .locator('button[title="Delete Department"]')
      .first();
    await firstDeleteButton.click();

    // Wait for confirmation dialog
    await expect(
      page.locator("text=Are you sure you want to delete this department?")
    ).toBeVisible();

    // Confirm deletion
    await page.click('button:has-text("Yes, Delete")');

    // Wait for success message
    await expect(page.locator("text=Deleted successfully")).toBeVisible({
      timeout: 10000,
    });

    // Verify row count decreased
    const newRowCount = await page.locator('[role="row"]').count();
    expect(newRowCount).toBeLessThan(initialRowCount);
  });

  test("should show correct columns in department table", async ({ page }) => {
    // Check for expected column headers
    await expect(page.locator("text=Name")).toBeVisible();
    await expect(page.locator("text=Code")).toBeVisible();
    await expect(page.locator("text=Description")).toBeVisible();
    await expect(page.locator("text=Actions")).toBeVisible();
  });
});
