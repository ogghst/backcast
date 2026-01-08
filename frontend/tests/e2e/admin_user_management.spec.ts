import { test, expect } from "@playwright/test";

test.describe("Admin User Management", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');

    // Wait for redirect to home
    await page.waitForURL("/");
    await page.waitForLoadState("networkidle");

    // Navigate to Admin > User Management
    const adminMenu = page.locator("aside").getByText("Admin", { exact: true });
    await adminMenu.click();
    await page.locator("aside").getByText("User Management").click();
    await page.waitForURL(/\/admin\/users/);
    await page.goto("/admin/users?per_page=100");
    await page.waitForLoadState("networkidle");
    await page.goto("/admin/users?per_page=100");
    await page.waitForLoadState("networkidle");
  });

  test("should display user management page with table", async ({ page }) => {
    // Check page title (specific to content area)
    await expect(
      page.locator("main").getByText("User Management", { exact: true })
    ).toBeVisible();

    // Check table is visible
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    // Check Add User button
    await expect(page.locator('button:has-text("Add User")')).toBeVisible();
  });

  test("should create a new user", async ({ page }) => {
    // Click Add User button
    await page.click('button:has-text("Add User")');

    // Wait for modal
    await expect(page.locator('[role="dialog"]')).toBeVisible();

    const timestamp = Date.now();
    const testName = `Test E2E User ${timestamp}`;
    const testEmail = `e2e_${timestamp}@test.com`;

    // Fill in user form
    await page.fill('input[placeholder="John Doe"]', testName);
    await page.fill('input[placeholder="john@example.com"]', testEmail);
    await page.fill('input[placeholder="Password"]', "password123");

    // Select role
    await page.locator("#user_form_role").click();
    await page.click(".ant-select-item-option-content:has-text('Viewer')");

    // Submit form
    await page.click('button:has-text("Create")');

    // Wait for modal to close instead of toast
    await expect(page.locator(".ant-modal-content")).not.toBeVisible({
      timeout: 15000,
    });

    // Verify user appears in table
    await expect(page.locator(`text=${testName}`).first()).toBeVisible({
      timeout: 15000,
    });
  });

  test("should edit an existing user", async ({ page }) => {
    // 1. Create a user to edit
    const timestamp = Date.now();
    const testName = `Edit Target ${timestamp}`;
    const testEmail = `edit_${timestamp}@test.com`;

    await page.click('button:has-text("Add User")');
    await page.fill('input[placeholder="John Doe"]', testName);
    await page.fill('input[placeholder="john@example.com"]', testEmail);
    await page.fill('input[placeholder="Password"]', "password123");
    await page.locator("#user_form_role").click();
    await page.click(".ant-select-item-option-content:has-text('Viewer')");
    await page.click('button:has-text("Create")');
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();
    await expect(page.locator(`text=${testName}`).first()).toBeVisible({
      timeout: 10000,
    });

    // 2. Find and click edit button for our user
    const row = page.locator(`tr:has-text("${testEmail}")`).first();
    const editButton = row.locator('button[title="Edit User"]');
    await editButton.click();

    // Wait for modal
    await expect(page.locator('[role="dialog"]')).toBeVisible();

    // Modify the name
    const updatedName = `Updated ${testName}`;
    const nameInput = page.locator('input[placeholder="John Doe"]');
    await nameInput.clear();
    await nameInput.fill(updatedName);

    // Submit form
    await page.click('button:has-text("Save")');

    // Wait for modal to close
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify update reflected in table
    await expect(page.locator(`text=${updatedName}`).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("should show history drawer when clicking history button", async ({
    page,
  }) => {
    // 1. Create a user to have history for
    const timestamp = Date.now();
    const testName = `History User ${timestamp}`;
    const testEmail = `history_${timestamp}@test.com`;

    await page.click('button:has-text("Add User")');
    await page.fill('input[placeholder="John Doe"]', testName);
    await page.fill('input[placeholder="john@example.com"]', testEmail);
    await page.fill('input[placeholder="Password"]', "password123");
    await page.locator("#user_form_role").click();
    await page.click(".ant-select-item-option-content:has-text('Viewer')");
    await page.click('button:has-text("Create")');
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();
    await expect(page.locator(`text=${testName}`).first()).toBeVisible({
      timeout: 10000,
    });

    // 2. Click history button for our user
    const row = page.locator(`tr:has-text("${testEmail}")`).first();
    const historyButton = row.locator('button[title="View History"]');
    await historyButton.click();

    // Wait for drawer
    await expect(page.locator(`text=User: ${testName}`)).toBeVisible({
      timeout: 5000,
    });
  });

  test("should filter users using global search", async ({ page }) => {
    // 1. Create a unique user to search for
    const timestamp = Date.now();
    const uniqueName = `SearchTarget ${timestamp}`;
    const uniqueEmail = `search_${timestamp}@test.com`;

    await page.click('button:has-text("Add User")');
    await page.fill('input[placeholder="John Doe"]', uniqueName);
    await page.fill('input[placeholder="john@example.com"]', uniqueEmail);
    await page.fill('input[placeholder="Password"]', "password123");
    await page.locator("#user_form_role").click();
    await page.click(".ant-select-item-option-content:has-text('Viewer')");
    await page.click('button:has-text("Create")');

    await expect(page.locator(".ant-modal-content")).not.toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator(`text=${uniqueName}`).first()).toBeVisible({
      timeout: 15000,
    });

    // 2. Use Global Search
    const searchInput = page.locator('input[placeholder="Search users..."]');
    await expect(searchInput).toBeVisible();

    // Type unique part of name
    await searchInput.fill(`SearchTarget ${timestamp}`);
    // Wait for debounce (300ms) + react render
    await page.waitForTimeout(500);

    // Verify user is still visible
    await expect(page.locator(`text=${uniqueName}`).first()).toBeVisible();

    // 3. Search for something non-existent
    await searchInput.fill(`NonExistent_${timestamp}`);
    await page.waitForTimeout(500);

    // Verify user is NOT visible
    await expect(page.locator(`text=${uniqueName}`)).not.toBeVisible();

    // Verify "No data" or empty table (AntD usually shows "No Data")
    // Use .ant-empty-description or just ensure filtered out
    await expect(page.locator(".ant-empty-description")).toBeVisible();

    // 4. Clear search
    await searchInput.clear();
    await page.waitForTimeout(500);

    // Verify user is back
    await expect(page.locator(`text=${uniqueName}`).first()).toBeVisible();
  });

  test("should enforce RBAC - admin menu visible", async ({ page }) => {
    // Navigate to home
    await page.goto("/");

    // Admin menu should be visible in sidebar
    const adminMenu = page.locator("aside").getByText("Admin", { exact: true });
    await expect(adminMenu).toBeVisible();

    // Click to expand submenu
    await adminMenu.click();

    // Admin submenu items should be visible
    await expect(
      page.locator("aside").getByText("User Management", { exact: true })
    ).toBeVisible();
    await expect(
      page.locator("aside").getByText("Department Management", { exact: true })
    ).toBeVisible();
  });
});
