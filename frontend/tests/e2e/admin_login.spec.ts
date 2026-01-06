import { test, expect } from "@playwright/test";

test.describe("Admin Login & Profile Verification", () => {
  test("should login as admin and verify profile and permissions", async ({
    page,
  }) => {
    // 1. Navigate to login page
    await page.goto("/login");

    // 2. Fill in credentials
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");

    // 3. Click login
    await page.click('button[type="submit"]');

    // 4. Wait for navigation to dashboard
    await page.waitForURL("/");

    // Verify dashboard content is visible
    await expect(page.getByText("Backcast ©202")).toBeVisible();

    // 5. Verify User Profile
    // First, finding the avatar/profile dropdown trigger
    const profileTrigger = page.locator(".ant-dropdown-trigger").first();
    await expect(profileTrigger).toBeVisible();

    // 6. Click profile to open dropdown and see details
    await profileTrigger.click();

    // Wait for dropdown to be visible
    const dropdownMenu = page.locator(".ant-dropdown-menu");
    await expect(dropdownMenu).toBeVisible();

    // Verify Name inside dropdown (User Info menu item)
    await expect(dropdownMenu.getByText("System Administrator")).toBeVisible();

    // 7. Verify Role inside E2E
    // (Consolidated previous steps)

    // Verify Role inside dropdown
    await expect(page.getByText("admin", { exact: true })).toBeVisible();

    // 7. Verify Side Menu items (Admin specific)
    // Dashboard should always be there
    await expect(
      page.getByRole("menuitem", { name: "Dashboard" })
    ).toBeVisible();

    // "Users" menu item should be visible for admin (from AppLayout.tsx logic)
    // Admin menu item should be visible in sidebar for admin
    const adminMenu = page.locator("aside").getByText("Admin", { exact: true });
    await expect(adminMenu).toBeVisible();

    // Verify Role inside dropdown
    await expect(
      dropdownMenu.getByText("admin", { exact: true })
    ).toBeVisible();

    // Expand Admin menu to see User Management
    await adminMenu.click();
    await expect(
      page.locator("aside").getByText("User Management")
    ).toBeVisible();

    // --- PHASE 2: Logout and Login as Viewer ---

    // 8. Logout
    // Click somewhere else to close any open menus, then reopen profile dropdown
    await page.mouse.click(0, 0);
    await page.waitForTimeout(500);

    // Reopen the profile dropdown
    await profileTrigger.click();
    await expect(dropdownMenu).toBeVisible();

    const logoutBtn = dropdownMenu
      .locator(".ant-dropdown-menu-item")
      .filter({ hasText: "Logout" });
    await expect(logoutBtn).toBeVisible();
    await logoutBtn.click();

    // 9. Wait for login page
    await page.waitForURL("/login");

    // 10. Login as Viewer
    await page.fill('input[id="login_email"]', "viewer@backcast.org");
    await page.fill('input[id="login_password"]', "backcast");
    await page.click('button[type="submit"]');

    // 11. Wait for navigation to dashboard
    await page.waitForURL("/");

    // 12. Verify Viewer Profile
    // Open profile dropdown
    // Note: Locator for trigger might need re-querying if page reloaded/navigated? Yes.
    const profileTriggerViewer = page.locator(".ant-dropdown-trigger").first();
    await expect(profileTriggerViewer).toBeVisible();
    await profileTriggerViewer.click();

    const dropdownMenuViewer = page.locator(".ant-dropdown-menu");
    await expect(dropdownMenuViewer).toBeVisible();

    // Verify Name is 'viewer' (it's in a <strong> tag)
    await expect(dropdownMenuViewer.locator("strong")).toHaveText("viewer");

    // Verify Role is 'viewer' (secondary text)
    await expect(
      dropdownMenuViewer.locator(".ant-typography-secondary")
    ).toHaveText("viewer");

    // Close dropdown to clear view? Or just proceed.
    // Click outside to close?
    await page.mouse.click(0, 0);

    // 13. Verify "Users" menu item is NOT visible
    // Verify "Admin" menu item is NOT visible in sidebar
    await expect(
      page.locator("aside").getByText("Admin", { exact: true })
    ).not.toBeVisible();

    // --- PHASE 3: Logout and Login as Admin Again ---

    // 14. Logout
    await profileTriggerViewer.click(); // Open dropdown
    await expect(dropdownMenuViewer).toBeVisible();
    const logoutBtnViewer = dropdownMenuViewer
      .locator(".ant-dropdown-menu-item")
      .filter({ hasText: "Logout" });
    await expect(logoutBtnViewer).toBeVisible();
    await logoutBtnViewer.click();

    await page.waitForURL("/login");

    // 15. Login as Admin
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');

    await page.waitForURL("/");

    // 16. Verify Admin Profile
    await expect(page.getByText("Backcast ©202")).toBeVisible();

    const profileTriggerAdmin = page.locator(".ant-dropdown-trigger").first();
    await profileTriggerAdmin.click();

    const dropdownMenuAdmin = page.locator(".ant-dropdown-menu");
    await expect(dropdownMenuAdmin).toBeVisible();

    await expect(
      dropdownMenuAdmin.getByText("System Administrator")
    ).toBeVisible();

    // Close dropdown
    await page.mouse.click(0, 0);

    // 17. Verify "Users" component/menu is present
    // Wait for Dashboard first to ensure menu is rendered
    await expect(
      page.getByRole("menuitem", { name: "Dashboard" })
    ).toBeVisible();
    const adminMenuAgain = page
      .locator("aside")
      .getByText("Admin", { exact: true });
    await expect(adminMenuAgain).toBeVisible();
    await adminMenuAgain.click();
    await expect(
      page.locator("aside").getByText("User Management")
    ).toBeVisible();
  });
});
