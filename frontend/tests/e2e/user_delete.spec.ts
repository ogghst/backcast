import { test, expect } from "@playwright/test";

test.describe("User Deletion", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await page.click('text="Users"');
    await page.waitForURL("/users");
  });

  test("should delete an existing user and reflect in UI", async ({ page }) => {
    // 1. Wait for user list to load
    await expect(page.locator("tr").first()).toBeVisible({ timeout: 10000 });

    // 2. Find any user in the table that is NOT the admin (to avoid deleting ourselves if possible)
    // Actually, for the test we can just delete the first one that has a delete button.
    const deleteButton = page.locator('button[title="Delete User"]').first();
    await expect(deleteButton).toBeVisible();

    // Get the email or ID of the user we are about to delete for verification
    const row = page.locator("tr", { has: deleteButton });
    const userEmail = await row.locator("td").nth(1).innerText();
    console.log(`Deleting user: ${userEmail}`);

    // 3. Click delete button
    await deleteButton.click();

    // 4. Confirm in the modal
    // Ant Design's modal.confirm/modal.info/etc all use .ant-modal
    const confirmModal = page.locator(".ant-modal").last();
    await expect(confirmModal).toBeVisible({ timeout: 10000 });

    // Find any button that looks like a confirmation (often has 'ant-btn-primary' or 'ant-btn-dangerous')
    const okButton = confirmModal
      .locator(
        'button:has-text("Delete"), button:has-text("Yes"), button:has-text("OK")'
      )
      .first();
    await okButton.click();

    // 5. Verify user is gone from UI
    await expect(page.locator(`text=${userEmail}`)).not.toBeVisible({
      timeout: 10000,
    });
  });
});
