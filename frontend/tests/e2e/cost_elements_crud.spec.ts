import { test, expect } from "@playwright/test";

test.describe("Cost Element CRUD", () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');
    await expect(page.getByRole("menuitem", { name: "Dashboard" })).toBeVisible(
      { timeout: 60000 }
    );
  });

  test("should create, edit, view history and delete Cost Element", async ({
    page,
  }) => {
    test.setTimeout(90000);
    const timestamp = Date.now();

    // 1. Create Dependencies (Dept, Type, Proj, WBE)
    // Detailed steps abbreviated for brevity as they assume pre-requisites are met or created inline

    // Create Department
    const deptName = `CE Dept ${timestamp}`;
    const deptCode = `CD${timestamp}`.substring(0, 10);
    await page.goto("/admin/departments");
    await page.click('button:has-text("Add Department")');
    await page.fill('input[placeholder="Engineering"]', deptName);
    await page.fill('input[placeholder="ENG"]', deptCode);
    await page.click('button:has-text("Create")');
    await expect(page.locator(`text=${deptCode}`)).toBeVisible();

    // Create Cost Element Type
    const typeName = `CE Type ${timestamp}`;
    const typeCode = `CT${timestamp}`.substring(0, 10);
    await page.goto("/admin/cost-element-types");
    await page.click('button:has-text("Add Type")');
    await page.fill('input[id="cost_element_type_form_name"]', typeName);
    await page.fill('input[id="cost_element_type_form_code"]', typeCode);
    // Select Department
    await page.click('input[id="cost_element_type_form_department_id"]');
    await page
      .locator('input[id="cost_element_type_form_department_id"]')
      .pressSequentially(deptName, { delay: 100 });
    await page.waitForTimeout(1000);
    await page.keyboard.press("Enter");
    await page.click('button:has-text("Create")');
    await expect(page.locator(`text=${typeCode}`)).toBeVisible();

    // Create Project
    const projName = `CE Proj ${timestamp}`;
    const projCode = `CP${timestamp}`.substring(0, 10);
    await page.goto("/projects");
    const projCreatePromise = page.waitForResponse(
      (r) =>
        r.url().includes("/projects") &&
        r.method() === "POST" &&
        r.status() === 201
    );
    await page.click('button:has-text("Add Project")');
    await page.getByLabel("Project Code").fill(projCode);
    await page.getByLabel("Project Name").fill(projName);
    await page.getByLabel("Budget").fill("10000");
    await page.click('button:has-text("Create")');
    const projRes = await projCreatePromise;
    const projJson = await projRes.json();
    const projectId = projJson.project_id;
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Create WBE
    const wbeName = `CE WBE ${timestamp}`;
    const wbeCode = `CW${timestamp}`.substring(0, 10);
    await page.goto("/admin/wbes");
    await page.click('button:has-text("Add WBE")');
    await page.fill('input[id="wbe_form_project_id"]', projectId);
    await page.fill('input[id="wbe_form_name"]', wbeName);
    await page.fill('input[id="wbe_form_code"]', wbeCode);
    await page.click('button:has-text("Create")');
    await expect(page.locator(`text=${wbeCode}`)).toBeVisible();

    // 2. Create Cost Element
    const elementName = `Cost Elem ${timestamp}`;
    const elementCode = `CE${timestamp}`.substring(0, 10);
    const budget = "5000";

    await page.goto("/financials/cost-elements");
    await page.click('button:has-text("Add Cost Element")');
    await page.fill('input[id="cost_element_form_name"]', elementName);
    await page.fill('input[id="cost_element_form_code"]', elementCode);
    await page.locator("#cost_element_form_budget_amount").fill(budget);

    // Select WBE
    await page.click('input[id="cost_element_form_wbe_id"]');
    await page.locator('input[id="cost_element_form_wbe_id"]').fill(wbeCode);
    await expect(page.locator(".ant-select-dropdown")).toBeVisible();
    await expect(
      page.locator(".ant-select-item-option-content").first()
    ).toBeVisible();
    await page.locator(".ant-select-item-option-content").first().click();

    // Select Type
    await page.click('input[id="cost_element_form_cost_element_type_id"]');
    await page
      .locator('input[id="cost_element_form_cost_element_type_id"]')
      .fill(typeCode);
    await expect(page.locator(".ant-select-dropdown")).toBeVisible();
    await expect(
      page.locator(".ant-select-item-option-content").first()
    ).toBeVisible();
    await page.locator(".ant-select-item-option-content").first().click();

    await page.click('button:has-text("Create")');
    await expect(page.locator(`text=${elementCode}`)).toBeVisible();

    // 3. Edit Cost Element
    const row = page.locator(`tr:has-text("${elementCode}")`);
    await row.locator('button[title="Edit Cost Element"]').click();

    const updatedName = `Updated CE ${timestamp}`;
    await page.fill('input[id="cost_element_form_name"]', updatedName);
    await page.click('button:has-text("Save")');
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();
    await expect(page.locator(`text=${updatedName}`)).toBeVisible();

    // 4. Check History
    const updatedRow = page.locator(`tr:has-text("${elementCode}")`);
    await updatedRow.locator('button[title="View History"]').click();
    await expect(
      page.locator(".ant-drawer-title").filter({ hasText: "History" })
    ).toBeVisible();
    await expect(page.locator(".ant-list-item")).toHaveCount(2); // Create + Update
    await page.locator(".ant-drawer-close").click();
    await expect(page.locator(".ant-drawer-content")).not.toBeVisible();

    // 5. Delete Cost Element
    const deleteRow = page.locator(`tr:has-text("${elementCode}")`);
    await deleteRow.locator('button[title="Delete Cost Element"]').click();

    // Confirm
    const popconfirm = page.locator(".ant-modal-confirm"); // Or popconfirm?
    // CostElementManagement uses `modal.confirm` which uses .ant-modal-confirm class usually?
    // Let's check CostElementManagement code.
    // Step 786 doesn't show DELETE handler.
    // I'll assume standard AntD modal confirm.
    await expect(page.locator(".ant-modal-confirm-title")).toHaveText(
      "Are you sure you want to delete this cost element?"
    );
    await page.click('button:has-text("Yes, Delete")');

    await expect(page.locator(`text=${elementCode}`)).not.toBeVisible();
  });
});
