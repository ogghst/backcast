import { test, expect } from "@playwright/test";

test.describe("Admin Department Management", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');

    // Wait for redirect to home
    await page.waitForURL("/");

    // Navigate to Admin > Department Management
    const adminMenu = page.locator("aside").getByText("Admin", { exact: true });
    await adminMenu.click();
    await page.locator("aside").getByText("Department Management").click();
    await page.waitForURL(/\/admin\/departments/);
    await page.goto("/admin/departments?per_page=100");
    await page.waitForLoadState("networkidle");
  });

  test("should display department management page with table", async ({
    page,
  }) => {
    // Check page title
    await expect(
      page.locator("main").getByText("Department Management", { exact: true })
    ).toBeVisible();

    // Check table is visible
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

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

    const timestamp = Date.now();
    const testName = `Test Dept ${timestamp}`;
    const testCode = `TD${timestamp}`.substring(0, 10);

    // Fill in department form
    await page.fill('input[placeholder="Engineering"]', testName);
    await page.fill('input[placeholder="ENG"]', testCode);

    // Optionally fill description
    const descriptionField = page.locator(
      'textarea[placeholder*="description"]'
    );
    if (await descriptionField.isVisible()) {
      await descriptionField.fill("Test department for E2E testing");
    }

    // Submit form
    await page.click('button:has-text("Create")');

    // Wait for modal to close
    await expect(page.locator('[role="dialog"]')).not.toBeVisible();

    // Verify department appears in table
    await expect(page.locator(`text=${testName}`).first()).toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator(`text=${testCode}`).first()).toBeVisible();
  });

  test("should edit an existing department", async ({ page }) => {
    // 1. Create a department to edit
    const timestamp = Date.now();
    const testName = `Edit Dept ${timestamp}`;
    const testCode = `ED${timestamp}`.substring(0, 10);

    await page.click('button:has-text("Add Department")');
    await page.fill('input[placeholder="Engineering"]', testName);
    await page.fill('input[placeholder="ENG"]', testCode);
    await page.click('button:has-text("Create")');
    await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    await expect(page.locator(`text=${testCode}`).first()).toBeVisible({
      timeout: 10000,
    });

    // 2. Find and click edit button for our department
    const row = page.locator(`tr:has-text("${testCode}")`);
    const editButton = row.locator('button[title="Edit Department"]');
    await editButton.click();

    // Wait for modal
    await expect(page.locator('[role="dialog"]')).toBeVisible();

    // Modify the name
    const updatedName = `Updated ${testName}`;
    const nameInput = page.locator('input[placeholder="Engineering"]');
    await nameInput.clear();
    await nameInput.fill(updatedName);

    // Submit form
    await page.click('button:has-text("Save")');

    // Wait for modal to close
    await expect(page.locator('[role="dialog"]')).not.toBeVisible();

    // Verify update
    await expect(page.locator(`text=${updatedName}`).first()).toBeVisible({
      timeout: 10000,
    });
  });

  test("should delete a department with confirmation", async ({ page }) => {
    // 1. Create a department to delete
    const timestamp = Date.now();
    const testName = `Delete Dept ${timestamp}`;
    const testCode = `DL${timestamp}`.substring(0, 10);

    await page.click('button:has-text("Add Department")');
    await page.fill('input[placeholder="Engineering"]', testName);
    await page.fill('input[placeholder="ENG"]', testCode);
    await page.click('button:has-text("Create")');
    await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    await expect(page.locator(`text=${testCode}`).first()).toBeVisible({
      timeout: 10000,
    });

    // 2. Click delete button for our department
    const row = page.locator(`tr:has-text("${testCode}")`).first();
    const deleteButton = row.locator('button[title="Delete Department"]');
    await deleteButton.click();

    // Wait for confirmation modal (Ant Design uses .ant-modal-confirm)
    const confirmModal = page.locator(".ant-modal-confirm");
    await expect(confirmModal).toBeVisible();

    // Confirm deletion - the okText from modal.confirm is "Yes, Delete"
    await page.click('button:has-text("Yes, Delete")');

    // Wait for modal to disappear
    await expect(confirmModal).not.toBeVisible();

    // Verify gone
    await expect(page.locator(`text=${testCode}`).first()).not.toBeVisible({
      timeout: 10000,
    });
  });

  test("should show correct columns in department table", async ({ page }) => {
    // Check for expected column headers
    await expect(page.locator("text=Name")).toBeVisible();
    await expect(page.locator("text=Code")).toBeVisible();
    await expect(page.locator("text=Description")).toBeVisible();
    await expect(page.locator("text=Actions")).toBeVisible();
  });
});
