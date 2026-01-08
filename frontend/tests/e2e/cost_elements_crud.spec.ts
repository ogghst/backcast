import { test, expect } from "@playwright/test";

test.describe("Cost Element CRUD", () => {
  test.describe.configure({ mode: "serial" });
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
    test.setTimeout(180000);
    const timestamp = Date.now();

    // 1. Create Dependencies (Dept, Type, Proj, WBE)
    // Detailed steps abbreviated for brevity as they assume pre-requisites are met or created inline

    const deptName = `CE Dept ${timestamp}`;
    const deptCode = `CD${timestamp}`.substring(0, 10);

    await page.goto("/admin/departments?per_page=100");
    await page.waitForLoadState("domcontentloaded");

    // Check if we are really on the page
    await expect(
      page.getByText("Department Management", { exact: true })
    ).toBeVisible({ timeout: 10000 });

    // Check if table loaded
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    // Check if user is loaded by looking for profile
    await expect(page.locator(".ant-dropdown-trigger").first()).toBeVisible();

    const addDeptBtn = page.getByRole("button", { name: "Add Department" });
    await expect(addDeptBtn).toBeVisible({ timeout: 10000 });

    await addDeptBtn.click();

    await expect(page.locator(".ant-modal-body").last()).toBeVisible({
      timeout: 10000,
    });
    await page.fill('input[placeholder="Engineering"]', deptName);
    await page.fill('input[placeholder="ENG"]', deptCode);

    const deptCreatePromise = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/departments") &&
        r.request().method() === "POST" &&
        r.status() === 201
    );

    await page.locator('.ant-modal-footer button:has-text("Create")').click();
    await deptCreatePromise;
    await expect(page.locator(".ant-modal-body")).not.toBeVisible();
    await expect(page.locator(`text=${deptCode}`).first()).toBeVisible({
      timeout: 15000,
    });

    // Create Cost Element Type
    const typeName = `CE Type ${timestamp}`;
    const typeCode = `CT${timestamp}`.substring(0, 10);
    const typeCreatePromise = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/cost-element-types") &&
        r.request().method() === "POST" &&
        r.status() === 201
    );
    await page.goto("/admin/cost-element-types?per_page=100");
    await page.waitForLoadState("load");
    await page.waitForTimeout(2000);

    await page.getByRole("button", { name: "Add Type" }).click({ force: true });

    // Give time for modal to open and data to fetch
    await page.waitForTimeout(2000);

    await expect(page.locator(".ant-modal-body").last()).toBeVisible({
      timeout: 10000,
    });
    await page.fill('input[id="cost_element_type_form_name"]', typeName);
    await page.fill('input[id="cost_element_type_form_code"]', typeCode);
    // Select Department
    await page.click('input[id="cost_element_type_form_department_id"]');
    await page
      .locator('input[id="cost_element_type_form_department_id"]')
      .fill(deptName);
    await expect(page.locator(".ant-select-dropdown")).toBeVisible();
    // Wait for the option with deptName
    const deptOption = page.locator(
      `.ant-select-item-option-content:has-text("${deptName}")`
    );

    await expect(deptOption).toBeVisible({ timeout: 10000 });
    await deptOption.click();

    // Verify selection
    // Note: AntD Select input value might not update to label text directly if mode is not combine?
    // But usually it shows the selected item.
    // Let's just trust the click for now or wait a bit.
    await page.waitForTimeout(500);

    await page.locator('.ant-modal-footer button:has-text("Create")').click();
    await typeCreatePromise;

    await expect(page.locator(".ant-modal-body")).not.toBeVisible();
    await expect(page.locator(`text=${typeCode}`)).toBeVisible({
      timeout: 30000,
    });

    // Create Project
    const projName = `CE Proj ${timestamp}`;
    const projCode = `CP${timestamp}`.substring(0, 10);
    await page.goto("/projects?per_page=100");
    await page.waitForLoadState("networkidle");
    const projCreatePromise = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/projects") &&
        r.request().method() === "POST" &&
        r.status() === 201
    );
    await page.waitForTimeout(500);
    await page.click('button:has-text("Add Project")', { force: true });
    await expect(page.locator(".ant-modal-body")).toBeVisible({
      timeout: 10000,
    });
    await page.getByLabel("Project Code").fill(projCode);
    await page.getByLabel("Project Name").fill(projName);
    await page.getByLabel("Budget").fill("10000");
    await page.locator('.ant-modal-footer button:has-text("Create")').click();
    const projRes = await projCreatePromise;
    const projJson = await projRes.json();
    const projectId = projJson.project_id;
    await expect(page.locator(".ant-modal-body")).not.toBeVisible();

    // Create WBE
    const wbeName = `CE WBE ${timestamp}`;
    const wbeCode = `CW${timestamp}`.substring(0, 10);
    await page.goto("/admin/wbes?per_page=100");
    const wbeCreatePromise = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/wbes") &&
        r.request().method() === "POST" &&
        r.status() === 201
    );
    await page.getByRole("button", { name: "Add WBE" }).click();
    await expect(page.locator(".ant-modal-body")).toBeVisible();
    await page.fill('input[id="wbe_form_project_id"]', projectId);
    await page.fill('input[id="wbe_form_name"]', wbeName);
    await page.fill('input[id="wbe_form_code"]', wbeCode);
    await page.locator('.ant-modal-footer button:has-text("Create")').click();
    await expect(page.locator(".ant-modal-body")).not.toBeVisible();
    const wbeRes = await wbeCreatePromise;
    const wbeJson = await wbeRes.json();
    const wbeId = wbeJson.wbe_id;
    await expect(page.locator(`text=${wbeCode}`)).toBeVisible({
      timeout: 15000,
    });

    // 2. Create Cost Element
    const elementName = `Cost Elem ${timestamp}`;
    const elementCode = `CE${timestamp}`.substring(0, 10);
    const budget = "5000";

    await page.goto(`/projects/${projectId}/wbes/${wbeId}`);
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
    await expect(page.locator(`text=${elementCode}`)).toBeVisible({
      timeout: 15000,
    });

    // Verify Search
    const searchInput = page.locator(
      'input[placeholder="Search cost elements..."]'
    );
    await expect(searchInput).toBeVisible();

    const searchResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/cost-elements") &&
        resp.url().includes(`search=${encodeURIComponent(elementCode)}`)
    );
    await searchInput.fill(elementCode);
    await searchResponse;
    await expect(page.locator(`text=${elementCode}`).first()).toBeVisible();

    const emptyResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/cost-elements") &&
        resp.url().includes("search=NON_EXISTENT")
    );
    await searchInput.fill("NON_EXISTENT_CE_123");
    await emptyResponse;
    await expect(page.locator(`text=${elementCode}`)).not.toBeVisible();

    const clearIcon = page.locator(".ant-input-clear-icon");
    const clearResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/cost-elements") &&
        !resp.url().includes("search=")
    );
    if (await clearIcon.isVisible()) {
      await clearIcon.click();
    } else {
      await searchInput.fill("");
    }
    await clearResponse;
    await expect(page.locator(`text=${elementCode}`).first()).toBeVisible();

    // 3. Edit Cost Element
    const row = page.locator(`tr:has-text("${elementCode}")`);
    await row.locator('button[title="Edit Cost Element"]').click();

    const updatedName = `Updated CE ${timestamp}`;
    await page.fill('input[id="cost_element_form_name"]', updatedName);
    await page.click('button:has-text("Save")');
    await expect(page.locator(".ant-modal-body")).not.toBeVisible();
    await expect(page.locator(`text=${updatedName}`)).toBeVisible();

    // 4. Check History
    const updatedRow = page.locator(`tr:has-text("${elementCode}")`);
    await updatedRow.locator('button[title="View History"]').click();
    await expect(
      page.locator(".ant-drawer-title").filter({ hasText: "History" })
    ).toBeVisible();
    await expect(page.locator(".ant-list-item")).toHaveCount(2, {
      timeout: 15000,
    });
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
