import { test, expect } from "@playwright/test";

test.describe("User Deletion", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    const adminMenu = page.locator("aside").getByText("Admin", { exact: true });
    await adminMenu.click();
    await page.locator("aside").getByText("User Management").click();
    await page.waitForURL(/\/admin\/users/);
    await page.goto("/admin/users?per_page=100");
    await page.waitForLoadState("networkidle");
  });

  test("should delete an existing user and reflect in UI", async ({ page }) => {
    // 1. Create a user to delete
    const timestamp = Date.now();
    const deleteEmail = `delete_${timestamp}@test.com`;
    const deleteName = `Delete Candidate ${timestamp}`;

    await page.click('button:has-text("Add User")');
    await expect(page.locator('[role="dialog"]')).toBeVisible();

    await page.fill('input[placeholder="John Doe"]', deleteName);
    await page.fill('input[placeholder="john@example.com"]', deleteEmail);
    await page.fill('input[placeholder="Password"]', "password123");

    // Select role
    await page.locator("#user_form_role").click();
    await page.click(".ant-select-item-option-content:has-text('Viewer')");

    // Submit
    await page.click('button:has-text("Create")');
    await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    await expect(page.locator(`text=${deleteName}`).first()).toBeVisible({
      timeout: 10000,
    });

    // 2. Find the row for this specific user
    const row = page.locator(`tr:has-text("${deleteEmail}")`).first();
    const deleteButton = row.locator('button[title="Delete User"]');

    // 3. Delete
    await deleteButton.click();

    // 4. Confirm
    const confirmModal = page.locator(".ant-modal").last();
    await expect(confirmModal).toBeVisible();

    const okButton = confirmModal
      .locator('button:has-text("Yes, Delete"), button:has-text("OK")') // Adjust based on actual button text "Yes, Delete"
      .first();
    await okButton.click();

    // 5. Verify gone
    await expect(page.locator(`text=${deleteEmail}`).first()).not.toBeVisible({
      timeout: 10000,
    });
  });
});
