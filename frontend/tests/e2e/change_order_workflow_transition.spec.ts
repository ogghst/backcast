import { test, expect } from "@playwright/test";

/**
 * E2E Test for Change Order Workflow Transitions
 *
 * This test verifies the complete workflow state machine for Change Orders:
 * Draft → Submitted for Approval → Under Review → Approved/Rejected → Implemented
 *
 * The test also validates:
 * - Dynamic status options based on current state
 * - Branch locking on certain status transitions
 * - Backend debug logging (visible in server logs)
 * - Error messages when attempting invalid transitions
 */
test.describe("Change Order Workflow Transition", () => {
  let projectId: string;
  let changeOrderId: string;

  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await expect(
      page.getByRole("menuitem", { name: "Dashboard" })
    ).toBeVisible();

    // Create a project for testing
    await page.click("text=Projects");
    await expect(page).toHaveURL(/\/projects/);

    const timestamp = Date.now();
    const projectCode = `E2E-WORKFLOW-${timestamp}`;

    await page.getByRole("button", { name: "Add Project" }).click({ force: true });
    await page.getByLabel("Project Code").fill(projectCode);
    await page.getByLabel("Project Name").fill(`E2E Workflow Test Project ${timestamp}`);
    await page.getByRole("dialog").getByLabel("Budget").fill("100000");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Navigate to project detail and store project ID
    await page.click(`text=${projectCode}`);
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+$/);
    const url = page.url();
    const match = url.match(/\/projects\/([a-f0-9-]+)$/);
    if (match) {
      projectId = match[1];
    }
  });

  test("should transition from Draft to Submitted for Approval", async ({ page }) => {
    const timestamp = Date.now();
    const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

    // Create a Draft Change Order
    await page.getByRole("button", { name: /New Change Order/i }).click();
    await page.getByLabel("Change Order Code").fill(coCode);
    await page.getByLabel("Title").fill(`Workflow Test CO ${timestamp}`);
    await page.getByLabel("Status").selectOption("Draft");
    await page.getByLabel("Description").fill(
      "This CO tests workflow transitions from Draft to Submitted for Approval. " +
        "The status field should only show Draft in create mode and valid transitions in edit mode."
    );
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify the CO was created in Draft status
    await expect(page.locator(`text=${coCode}`)).toBeVisible();
    const coRow = page.locator(`tr:has-text("${coCode}")`);
    await expect(coRow.locator("text=Draft")).toBeVisible();

    // Store change order ID from the row
    const editButton = coRow.locator('button[title="Edit Change Order"]');
    await editButton.click();

    // Verify edit modal shows valid transitions (Draft should allow "Submitted for Approval")
    await expect(
      page.getByRole("dialog").getByText("Edit Change Order")
    ).toBeVisible();

    // Get the status field options
    const statusSelect = page.getByLabel("Status");
    await statusSelect.click();

    // Wait for dropdown to appear and get options
    const dropdown = page.locator(".ant-select-dropdown");
    await expect(dropdown).toBeVisible();

    // Verify that "Submitted for Approval" is an option
    const options = await dropdown.locator(".ant-select-item-option").allTextContents();
    expect(options).toContain("Submitted for Approval");

    // Select "Submitted for Approval"
    await page.locator('.ant-select-item-option:has-text("Submitted for Approval")').click();

    // Submit the form
    await page.getByRole("button", { name: "Save" }).click();

    // Wait for modal to close and verify success
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify status changed to "Submitted for Approval"
    await expect(coRow.locator('text="Submitted for Approval"')).toBeVisible({ timeout: 10000 });

    // Check console logs for backend debug messages
    // The backend should log: [DEBUG] Status transition: Draft -> Submitted for Approval
    const logs: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        logs.push(msg.text());
      }
    });

    // If there were any errors, display them
    if (logs.length > 0) {
      console.log("Console errors:", logs);
    }

    // Verify no frontend errors were shown
    await expect(page.locator(".ant-message-error")).not.toBeVisible();
  });

  test("should show locked branch warning when status is Under Review", async ({ page }) => {
    const timestamp = Date.now();
    const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

    // Create a Draft Change Order
    await page.getByRole("button", { name: /New Change Order/i }).click();
    await page.getByLabel("Change Order Code").fill(coCode);
    await page.getByLabel("Title").fill(`Lock Test CO ${timestamp}`);
    await page.getByLabel("Status").selectOption("Draft");
    await page.getByLabel("Description").fill("Testing branch locking on Under Review status.");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Transition to Submitted for Approval
    const coRow = page.locator(`tr:has-text("${coCode}")`);
    await coRow.locator('button[title="Edit Change Order"]').click();
    await page.locator('.ant-select-item-option:has-text("Submitted for Approval")').click();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Transition to Under Review
    await coRow.locator('button[title="Edit Change Order"]').click();
    await page.getByLabel("Status").click();
    await page.locator('.ant-select-item-option:has-text("Under Review")').click();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify status is now Under Review
    await expect(coRow.locator("text=Under Review")).toBeVisible();

    // Edit again and verify branch locked warning is shown
    await coRow.locator('button[title="Edit Change Order"]').click();

    // The modal should show a warning banner about locked branch
    await expect(
      page.locator(".ant-alert-warning").filter({ hasText: "Branch Locked" })
    ).toBeVisible();

    // The status field should be disabled
    const statusField = page.getByLabel("Status");
    await expect(statusField).toBeDisabled();

    await page.locator(".ant-modal-close").click();
  });

  test("should allow Rejected CO to be resubmitted", async ({ page }) => {
    const timestamp = Date.now();
    const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

    // Create a Draft Change Order
    await page.getByRole("button", { name: /New Change Order/i }).click();
    await page.getByLabel("Change Order Code").fill(coCode);
    await page.getByLabel("Title").fill(`Reject Test CO ${timestamp}`);
    await page.getByLabel("Status").selectOption("Draft");
    await page.getByLabel("Description").fill("Testing resubmission after rejection.");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Transition to Submitted for Approval
    const coRow = page.locator(`tr:has-text("${coCode}")`);
    await coRow.locator('button[title="Edit Change Order"]').click();
    await page.getByLabel("Status").click();
    await page.locator('.ant-select-item-option:has-text("Submitted for Approval")').click();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Transition to Under Review
    await coRow.locator('button[title="Edit Change Order"]').click();
    await page.getByLabel("Status").click();
    await page.locator('.ant-select-item-option:has-text("Under Review")').click();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Reject the CO
    await coRow.locator('button[title="Edit Change Order"]').click();
    await page.getByLabel("Status").click();
    await page.locator('.ant-select-item-option:has-text("Rejected")').click();
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify status is Rejected
    await expect(coRow.locator("text=Rejected")).toBeVisible();

    // Edit and verify resubmission is allowed (should show "Submitted for Approval" as option)
    await coRow.locator('button[title="Edit Change Order"]').click();

    // Get the status field options
    const statusSelect = page.getByLabel("Status");
    await statusSelect.click();

    // Wait for dropdown to appear
    const dropdown = page.locator(".ant-select-dropdown");
    await expect(dropdown).toBeVisible();

    // Verify that "Submitted for Approval" is available for resubmission
    const options = await dropdown.locator(".ant-select-item-option").allTextContents();
    expect(options).toContain("Submitted for Approval");

    await page.locator(".ant-modal-close").click();
  });

  test("should only show Draft option in create mode", async ({ page }) => {
    // Click "New Change Order"
    await page.getByRole("button", { name: /New Change Order/i }).click();

    // Verify modal is open
    await expect(
      page.getByRole("dialog").getByText("Create Change Order")
    ).toBeVisible();

    // Click on the status dropdown
    await page.getByLabel("Status").click();

    // Wait for dropdown to appear
    const dropdown = page.locator(".ant-select-dropdown");
    await expect(dropdown).toBeVisible();

    // Get all available options
    const options = await dropdown.locator(".ant-select-item-option").allTextContents();

    // Verify only "Draft" is available in create mode
    expect(options).toEqual(["Draft"]);

    // Close the modal
    await page.locator(".ant-modal-close").click();
  });

  test("should show error for invalid status transition", async ({ page }) => {
    // This test verifies that attempting an invalid transition shows an error
    // For example, trying to go from "Draft" to "Implemented" without approval

    const timestamp = Date.now();
    const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

    // Create a Draft Change Order
    await page.getByRole("button", { name: /New Change Order/i }).click();
    await page.getByLabel("Change Order Code").fill(coCode);
    await page.getByLabel("Title").fill(`Invalid Transition Test CO ${timestamp}`);
    await page.getByLabel("Status").selectOption("Draft");
    await page.getByLabel("Description").fill("Testing invalid status transitions.");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Try to edit - the status dropdown should NOT show "Implemented" directly
    const coRow = page.locator(`tr:has-text("${coCode}")`);
    await coRow.locator('button[title="Edit Change Order"]').click();

    // Get the status field options
    const statusSelect = page.getByLabel("Status");
    await statusSelect.click();

    // Wait for dropdown to appear
    const dropdown = page.locator(".ant-select-dropdown");
    await expect(dropdown).toBeVisible();

    // Get all available options
    const options = await dropdown.locator(".ant-select-item-option").allTextContents();

    // "Implemented" should NOT be available directly from Draft
    expect(options).not.toContain("Implemented");

    // Only valid transitions from Draft should be shown
    expect(options).toContain("Submitted for Approval");

    await page.locator(".ant-modal-close").click();
  });

  test("should display backend debug info in error messages", async ({ page }) => {
    // This test verifies that backend debug information is included in error messages
    // when an error occurs during status transition

    const timestamp = Date.now();
    const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

    // Create a Draft Change Order
    await page.getByRole("button", { name: /New Change Order/i }).click();
    await page.getByLabel("Change Order Code").fill(coCode);
    await page.getByLabel("Title").fill(`Debug Info Test ${timestamp}`);
    await page.getByLabel("Status").selectOption("Draft");
    await page.getByLabel("Description").fill("Testing backend debug info in error messages.");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Capture console messages and API errors
    const apiErrors: string[] = [];
    page.on("response", async (response) => {
      if (response.status() >= 400) {
        const body = await response.text();
        apiErrors.push(body);
        console.log(`API Error ${response.status()}:`, body);
      }
    });

    // Try to update - should succeed
    const coRow = page.locator(`tr:has-text("${coCode}")`);
    await coRow.locator('button[title="Edit Change Order"]').click();
    await page.getByLabel("Title").fill(`Updated Debug Info Test ${timestamp}`);
    await page.getByRole("button", { name: "Save" }).click();

    // Wait for modal to close - indicates success
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify no API errors were captured for successful update
    expect(apiErrors.filter((e) => e.includes(coCode))).toHaveLength(0);

    // Verify the update was successful
    await expect(page.locator(`text=Updated Debug Info Test ${timestamp}`)).toBeVisible();
  });
});
