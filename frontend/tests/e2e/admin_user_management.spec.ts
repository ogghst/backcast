import { test, expect } from "@playwright/test";

test.describe("Admin User Management", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[type="email"]', "admin@example.com");
    await page.fill('input[type="password"]', "admin123");
    await page.click('button[type="submit"]');

    // Wait for redirect to home
    await page.waitForURL("/");

    // Navigate to Admin > User Management
    await page.click("text=Admin");
    await page.click("text=User Management");
    await page.waitForURL("/admin/users");
  });

  test("should display user management page with table", async ({ page }) => {
    // Check page title
    await expect(page.locator("text=User Management")).toBeVisible();

    // Check table is visible
    await expect(page.locator('[role="table"]')).toBeVisible();

    // Check Add User button
    await expect(page.locator('button:has-text("Add User")')).toBeVisible();
  });

  test("should create a new user", async ({ page }) => {
    // Click Add User button
    await page.click('button:has-text("Add User")');

    // Wait for modal
    await expect(page.locator('[role="dialog"]')).toBeVisible();

    // Fill in user form
    await page.fill('input[placeholder="John Doe"]', "Test E2E User");
    await page.fill('input[placeholder="john@example.com"]', "e2e@test.com");
    await page.fill('input[placeholder="Password"]', "password123");

    // Select role
    await page.click("text=Select a role");
    await page.click("text=Viewer");

    // Submit form
    await page.click('button:has-text("Create")');

    // Wait for success message
    await expect(page.locator("text=Created successfully")).toBeVisible({
      timeout: 10000,
    });

    // Verify user appears in table
    await expect(page.locator("text=Test E2E User")).toBeVisible();
  });

  test("should edit an existing user", async ({ page }) => {
    // Find and click edit button for the first user
    const firstEditButton = page.locator('button[title="Edit User"]').first();
    await firstEditButton.click();

    // Wait for modal
    await expect(page.locator('[role="dialog"]')).toBeVisible();

    // Modify the name
    const nameInput = page.locator('input[value*=""]').first();
    await nameInput.clear();
    await nameInput.fill("Updated Name");

    // Submit form
    await page.click('button:has-text("Save")');

    // Wait for success message
    await expect(page.locator("text=Updated successfully")).toBeVisible({
      timeout: 10000,
    });
  });

  test("should show history drawer when clicking history button", async ({
    page,
  }) => {
    // Click history button for first user
    const historyButton = page.locator('button[title="View History"]').first();
    await historyButton.click();

    // Wait for drawer
    await expect(
      page.locator("text=Version History").or(page.locator("text=User:"))
    ).toBeVisible({ timeout: 5000 });
  });

  test("should enforce RBAC - admin menu visible", async ({ page }) => {
    // Navigate to home
    await page.goto("/");

    // Admin menu should be visible
    await expect(page.locator("text=Admin")).toBeVisible();

    // Click to expand submenu
    await page.click("text=Admin");

    // Admin submenu items should be visible
    await expect(page.locator("text=User Management")).toBeVisible();
    await expect(page.locator("text=Department Management")).toBeVisible();
  });
});
