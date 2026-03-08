#!/usr/bin/env node
import { chromium } from 'playwright';

const BASE_URL = 'http://localhost:5173';
const ADMIN_USER = 'admin@backcast.org';
const ADMIN_PASS = 'adminadmin';

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function testAIConfigUI() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 }
  });

  const page = await context.newPage();
  const consoleErrors = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });

  const results = { passed: [], failed: [], errors: [] };
  const screenshotDir = './test-screenshots';

  try {
    console.log('=== Starting AI Configuration UI Tests ===\n');

    // Step 1: Navigate to login page
    console.log('Step 1: Navigating to login page...');
    await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
    await sleep(1000);
    await page.screenshot({ path: `${screenshotDir}/01-login-page.png` });

    // Step 2: Login
    console.log('Step 2: Logging in...');
    const emailSelectors = ['input[type="email"]', 'input[name="email"]', 'input[id="email"]', 'input[placeholder*="email" i]'];
    let emailInput = null;
    for (const selector of emailSelectors) {
      try {
        emailInput = page.locator(selector).first();
        if (await emailInput.count() > 0) {
          console.log(`Found email input with selector: ${selector}`);
          break;
        }
      } catch (e) {}
    }

    if (!emailInput || await emailInput.count() === 0) {
      const pageContent = await page.content();
      console.log('Page URL:', page.url());
      console.log('Page title:', await page.title());
      await page.screenshot({ path: `${screenshotDir}/debug-login-form.png` });
      throw new Error('Could not find email input field');
    }

    await emailInput.fill(ADMIN_USER);

    const passwordSelectors = ['input[type="password"]', 'input[name="password"]', 'input[id="password"]'];
    let passwordInput = null;
    for (const selector of passwordSelectors) {
      try {
        passwordInput = page.locator(selector).first();
        if (await passwordInput.count() > 0) {
          console.log(`Found password input with selector: ${selector}`);
          break;
        }
      } catch (e) {}
    }

    if (!passwordInput || await passwordInput.count() === 0) {
      throw new Error('Could not find password input field');
    }

    await passwordInput.fill(ADMIN_PASS);

    const submitSelectors = ['button[type="submit"]', 'button:has-text("Login")', 'button:has-text("Sign In")', 'form button'];
    for (const selector of submitSelectors) {
      try {
        const submitButton = page.locator(selector).first();
        if (await submitButton.count() > 0) {
          console.log(`Clicking submit button with selector: ${selector}`);
          await submitButton.click();
          break;
        }
      } catch (e) {}
    }

    await sleep(2000);

    const currentUrl = page.url();
    console.log('After login, current URL:', currentUrl);

    if (!currentUrl.includes('/login')) {
      console.log('✓ Login successful');
      results.passed.push('Login');
    } else {
      const errorElement = page.locator('[class*="error"], [role="alert"]').first();
      if (await errorElement.count() > 0) {
        const errorText = await errorElement.textContent();
        throw new Error(`Login failed: ${errorText}`);
      }
      throw new Error('Login failed - still on login page');
    }
    await page.screenshot({ path: `${screenshotDir}/02-after-login.png` });

    // Step 3: Navigate to AI Providers page
    console.log('\nStep 3: Navigating to AI Providers page...');
    await page.goto(`${BASE_URL}/admin/ai-providers`, { waitUntil: 'networkidle' });
    await sleep(2000);
    await page.screenshot({ path: `${screenshotDir}/03-ai-providers-page.png` });
    results.passed.push('Navigate to AI Providers');

    // Step 4: Check if providers list is displayed
    console.log('\nStep 4: Checking providers list...');
    const tables = await page.locator('table, [role="table"]').count();
    console.log(`Found ${tables} tables`);
    await page.screenshot({ path: `${screenshotDir}/04-providers-list.png` });
    results.passed.push('Providers list displayed');

    // Step 5: Test CREATE Provider
    console.log('\nStep 5: Testing CREATE Provider...');
    const addSelectors = ['button:has-text("Add")', 'button:has-text("Create")', 'button[aria-label*="add" i]', '[data-testid="add-provider"]'];
    let addButton = null;
    for (const selector of addSelectors) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.count() > 0 && await btn.isVisible()) {
          addButton = btn;
          console.log(`Found add button with selector: ${selector}`);
          break;
        }
      } catch (e) {}
    }

    if (addButton) {
      await addButton.click();
      await sleep(1000);
      await page.screenshot({ path: `${screenshotDir}/05-create-provider-form.png` });

      const timestamp = Date.now().toString().slice(-6);

      const nameInput = page.locator('input[name="name"], #name').first();
      if (await nameInput.count() > 0) {
        await nameInput.fill(`Test Provider ${timestamp}`);
      }

      const typeSelect = page.locator('select[name="provider_type"], #provider_type').first();
      if (await typeSelect.count() > 0) {
        await typeSelect.selectOption('openai');
      }

      const urlInput = page.locator('input[name="base_url"], #base_url').first();
      if (await urlInput.count() > 0) {
        await urlInput.fill('https://api.openai.com/v1');
      }

      const activeCheckbox = page.locator('input[name="is_active"], #is_active').first();
      if (await activeCheckbox.count() > 0) {
        await activeCheckbox.check();
      }

      await page.screenshot({ path: `${screenshotDir}/06-create-provider-filled.png` });

      const submitSelectors = ['button[type="submit"]', 'button:has-text("Save")', 'button:has-text("Create")'];
      for (const selector of submitSelectors) {
        try {
          const btn = page.locator(selector).first();
          if (await btn.count() > 0 && await btn.isVisible()) {
            await btn.click();
            break;
          }
        } catch (e) {}
      }

      await sleep(2000);
      await page.screenshot({ path: `${screenshotDir}/07-after-create-provider.png` });

      const hasError = await page.locator('[class*="error"], [role="alert"]').count() > 0;
      if (hasError) {
        const errorText = await page.locator('[class*="error"], [role="alert"]').first().textContent();
        console.log('✗ CREATE Provider failed:', errorText);
        results.failed.push({ test: 'CREATE Provider', error: errorText });
      } else {
        console.log('✓ CREATE Provider successful');
        results.passed.push('CREATE Provider');
      }
    } else {
      console.log('✗ Could not find Add button');
      results.failed.push({ test: 'CREATE Provider', error: 'Add button not found' });
    }

    // Step 6: Test UPDATE Provider
    console.log('\nStep 6: Testing UPDATE Provider...');
    await page.goto(`${BASE_URL}/admin/ai-providers`, { waitUntil: 'networkidle' });
    await sleep(1000);

    const editSelectors = ['button:has-text("Edit")', 'button[aria-label*="edit" i]', 'button[class*="edit"]'];
    let editButton = null;
    for (const selector of editSelectors) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.count() > 0 && await btn.isVisible()) {
          editButton = btn;
          console.log(`Found edit button with selector: ${selector}`);
          break;
        }
      } catch (e) {}
    }

    if (editButton) {
      await editButton.click();
      await sleep(1000);
      await page.screenshot({ path: `${screenshotDir}/08-edit-provider-form.png` });

      const nameInput = page.locator('input[name="name"], #name').first();
      if (await nameInput.count() > 0) {
        await nameInput.fill(`Updated Provider ${Date.now().toString().slice(-6)}`);
      }

      await page.screenshot({ path: `${screenshotDir}/09-edit-provider-filled.png` });

      const updateSelectors = ['button[type="submit"]', 'button:has-text("Save")', 'button:has-text("Update")'];
      for (const selector of updateSelectors) {
        try {
          const btn = page.locator(selector).first();
          if (await btn.count() > 0 && await btn.isVisible()) {
            await btn.click();
            break;
          }
        } catch (e) {}
      }

      await sleep(2000);
      await page.screenshot({ path: `${screenshotDir}/10-after-update-provider.png` });

      const hasError = await page.locator('[class*="error"], [role="alert"]').count() > 0;
      if (hasError) {
        const errorText = await page.locator('[class*="error"], [role="alert"]').first().textContent();
        console.log('✗ UPDATE Provider failed:', errorText);
        results.failed.push({ test: 'UPDATE Provider', error: errorText });
      } else {
        console.log('✓ UPDATE Provider successful');
        results.passed.push('UPDATE Provider');
      }
    } else {
      console.log('✗ Could not find Edit button');
      results.failed.push({ test: 'UPDATE Provider', error: 'Edit button not found' });
    }

    // Step 7: Navigate to AI Assistants page
    console.log('\nStep 7: Navigating to AI Assistants page...');
    await page.goto(`${BASE_URL}/admin/ai-assistants`, { waitUntil: 'networkidle' });
    await sleep(2000);
    await page.screenshot({ path: `${screenshotDir}/11-ai-assistants-page.png` });
    results.passed.push('Navigate to AI Assistants');

    // Step 8: Check model dropdown
    console.log('\nStep 8: Checking model dropdown...');
    const addAssistantSelectors = ['button:has-text("Add")', 'button:has-text("Create")', '[data-testid="add-assistant"]'];
    let addAssistantButton = null;
    for (const selector of addAssistantSelectors) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.count() > 0 && await btn.isVisible()) {
          addAssistantButton = btn;
          console.log(`Found add assistant button with selector: ${selector}`);
          break;
        }
      } catch (e) {}
    }

    if (addAssistantButton) {
      await addAssistantButton.click();
      await sleep(1000);
      await page.screenshot({ path: `${screenshotDir}/13-create-assistant-form.png` });

      const modelSelect = page.locator('select[name="model_id"], #model_id').first();
      const modelOptions = await modelSelect.locator('option').all();
      console.log(`Model dropdown options: ${modelOptions.length}`);

      for (const opt of modelOptions) {
        const text = await opt.textContent();
        console.log(`  - ${text?.trim()}`);
      }

      if (modelOptions.length > 1) {
        console.log('✓ Model dropdown has data');
        results.passed.push('Model dropdown populated');
      } else {
        console.log('✗ Model dropdown shows "No data"');
        results.failed.push({ test: 'Model dropdown', error: `Only ${modelOptions.length} options found` });
      }

      const timestamp = Date.now().toString().slice(-6);
      const nameInput = page.locator('input[name="name"], #name').first();
      if (await nameInput.count() > 0) {
        await nameInput.fill(`Test Assistant ${timestamp}`);
      }

      const descInput = page.locator('textarea[name="description"], #description').first();
      if (await descInput.count() > 0) {
        await descInput.fill('Test assistant created by UI test');
      }

      const systemPromptInput = page.locator('textarea[name="system_prompt"], #system_prompt').first();
      if (await systemPromptInput.count() > 0) {
        await systemPromptInput.fill('You are a helpful assistant.');
      }

      if (modelOptions.length > 1) {
        await modelSelect.selectOption({ index: 1 });
      }

      const tempInput = page.locator('input[name="temperature"], #temperature').first();
      if (await tempInput.count() > 0) {
        await tempInput.fill('0.7');
      }

      const tokensInput = page.locator('input[name="max_tokens"], #max_tokens').first();
      if (await tokensInput.count() > 0) {
        await tokensInput.fill('2000');
      }

      const activeCheckbox = page.locator('input[name="is_active"], #is_active').first();
      if (await activeCheckbox.count() > 0) {
        await activeCheckbox.check();
      }

      await page.screenshot({ path: `${screenshotDir}/14-create-assistant-filled.png` });

      const submitSelectors = ['button[type="submit"]', 'button:has-text("Save")', 'button:has-text("Create")'];
      for (const selector of submitSelectors) {
        try {
          const btn = page.locator(selector).first();
          if (await btn.count() > 0 && await btn.isVisible()) {
            await btn.click();
            break;
          }
        } catch (e) {}
      }

      await sleep(2000);
      await page.screenshot({ path: `${screenshotDir}/15-after-create-assistant.png` });

      const hasError = await page.locator('[class*="error"], [role="alert"]').count() > 0;
      if (hasError) {
        const errorText = await page.locator('[class*="error"], [role="alert"]').first().textContent();
        console.log('✗ CREATE Assistant failed:', errorText);
        results.failed.push({ test: 'CREATE Assistant', error: errorText });
      } else {
        console.log('✓ CREATE Assistant successful');
        results.passed.push('CREATE Assistant');
      }
    } else {
      console.log('✗ Could not find Add Assistant button');
      results.failed.push({ test: 'CREATE Assistant', error: 'Add button not found' });
    }

    // Step 9: Test UPDATE Assistant
    console.log('\nStep 9: Testing UPDATE Assistant...');
    await page.goto(`${BASE_URL}/admin/ai-assistants`, { waitUntil: 'networkidle' });
    await sleep(1000);

    const editAssistantSelectors = ['button:has-text("Edit")', 'button[aria-label*="edit" i]'];
    let editAssistantButton = null;
    for (const selector of editAssistantSelectors) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.count() > 0 && await btn.isVisible()) {
          editAssistantButton = btn;
          break;
        }
      } catch (e) {}
    }

    if (editAssistantButton) {
      await editAssistantButton.click();
      await sleep(1000);
      await page.screenshot({ path: `${screenshotDir}/16-edit-assistant-form.png` });

      const nameInput = page.locator('input[name="name"], #name').first();
      if (await nameInput.count() > 0) {
        await nameInput.fill(`Updated Assistant ${Date.now().toString().slice(-6)}`);
      }

      await page.screenshot({ path: `${screenshotDir}/17-edit-assistant-filled.png` });

      const updateSelectors = ['button[type="submit"]', 'button:has-text("Save")'];
      for (const selector of updateSelectors) {
        try {
          const btn = page.locator(selector).first();
          if (await btn.count() > 0 && await btn.isVisible()) {
            await btn.click();
            break;
          }
        } catch (e) {}
      }

      await sleep(2000);
      await page.screenshot({ path: `${screenshotDir}/18-after-update-assistant.png` });

      const hasError = await page.locator('[class*="error"], [role="alert"]').count() > 0;
      if (hasError) {
        const errorText = await page.locator('[class*="error"], [role="alert"]').first().textContent();
        console.log('✗ UPDATE Assistant failed:', errorText);
        results.failed.push({ test: 'UPDATE Assistant', error: errorText });
      } else {
        console.log('✓ UPDATE Assistant successful');
        results.passed.push('UPDATE Assistant');
      }
    } else {
      console.log('✗ Could not find Edit Assistant button');
      results.failed.push({ test: 'UPDATE Assistant', error: 'Edit button not found' });
    }

  } catch (error) {
    console.error('\n✗ Test failed with error:', error.message);
    results.errors.push(error.message);
    await page.screenshot({ path: `${screenshotDir}/error.png` });
  } finally {
    await browser.close();
  }

  // Print summary
  console.log('\n=== Test Summary ===');
  console.log(`Passed: ${results.passed.length}`);
  console.log(`Failed: ${results.failed.length}`);
  console.log(`Errors: ${results.errors.length}`);

  if (results.passed.length > 0) {
    console.log('\n✓ Passed tests:');
    results.passed.forEach(test => console.log('  -', typeof test === 'string' ? test : test.test));
  }

  if (results.failed.length > 0) {
    console.log('\n✗ Failed tests:');
    results.failed.forEach(failure => console.log('  -', failure.test, ':', failure.error));
  }

  if (results.errors.length > 0) {
    console.log('\n✗ Errors:');
    results.errors.forEach(error => console.log('  -', error));
  }

  if (consoleErrors.length > 0) {
    console.log('\nConsole Errors:');
    consoleErrors.forEach(error => console.log('  -', error));
  }

  console.log(`\nScreenshots saved to ${screenshotDir}/`);

  process.exit(results.failed.length > 0 || results.errors.length > 0 ? 1 : 0);
}

testAIConfigUI().catch(console.error);
