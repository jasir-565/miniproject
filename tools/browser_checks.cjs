/* Runs only against the synthetic, disposable preview server. */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.PREVIEW_URL || 'http://127.0.0.1:8765';
assert(['localhost', '127.0.0.1'].includes(new URL(base).hostname));
const output = process.env.SCREENSHOT_DIR || 'test-results';
fs.mkdirSync(output, { recursive: true });
(async () => {
  for (let attempt = 0; attempt < 30; attempt++) {
    try { if ((await fetch(base)).ok) break; } catch {}
    if (attempt === 29) throw new Error('Preview server did not start');
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`${base}/bookings/1/estimate/?preview_role=staff`);
    await page.locator('[name="lines-0-kind"]').selectOption('LABOUR');
    await page.locator('[name="lines-0-description"]').fill('Inspection and engine oil service');
    await page.locator('[name="lines-0-quantity"]').fill('1');
    await page.locator('[name="lines-0-unit_price"]').fill('1250.00');
    await page.getByRole('button', { name: /Send estimate/ }).click();
    await page.goto(`${base}/bookings/1/estimated-bill/?preview_role=customer`);
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height: 1000});
      for (const [name, route] of [['active-bookings', '/my-bookings/'], ['pending-estimates', '/estimates/'], ['pending-bill', '/bookings/1/estimated-bill/'], ['book-service', '/service-booking/']]) {
        const response = await page.goto(base + route);
        assert.equal(response.status(), 200);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${name} overflows at ${width}px`);
        await page.screenshot({path: `${output}/${name}-${width}.png`, fullPage: true});
      }
    }
    await page.goto(`${base}/bookings/1/estimated-bill/`);
    await page.getByRole('button', { name: /Approve ₹/ }).click();
    assert.match(await page.locator('body').innerText(), /Approved/);
    await page.goto(`${base}/staff-dashboard/?preview_role=staff`);
    await page.locator('details').evaluateAll(items => items.forEach(item => item.open = true));
    const update = page.locator('form').filter({ has: page.locator('[name="current_work"]') }).first();
    await update.locator('[name="status"]').selectOption('IN_PROGRESS');
    await update.locator('[name="current_work"]').fill('Inspection complete; servicing underway.');
    await Promise.all([page.waitForNavigation(), update.evaluate(form => form.requestSubmit())]);
    await page.locator('details').evaluateAll(items => items.forEach(item => item.open = true));
    const complete = page.locator('form').filter({ has: page.locator('[name="inspection_details"]') }).first();
    await complete.locator('[name="inspection_details"]').fill('Inspected engine and fluid levels.');
    await complete.locator('[name="repair_details"]').fill('Engine oil service completed.');
    await complete.locator('[name="service_cost"]').fill('1250.00');
    await Promise.all([page.waitForNavigation(), complete.evaluate(form => form.requestSubmit())]);
    await page.goto(`${base}/bookings/1/receipt/?preview_role=customer`);
    assert.match(await page.locator('body').innerText(), /1250/);
    await page.screenshot({ path: `${output}/receipt.png`, fullPage: true });
    const routes = [['dashboard', '/dashboard/?preview_role=customer'], ['staff', '/staff-dashboard/?preview_role=staff'], ['roadside', '/roadside-assistance/?preview_role=customer'], ['timeline', '/bookings/1/?preview_role=customer'], ['account', '/account/?preview_role=customer']];
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const [name, route] of routes) {
        const response = await page.goto(base + route);
        assert.equal(response.status(), 200, route);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${name} overflows at ${width}px`);
        await page.screenshot({ path: `${output}/${name}-${width}.png`, fullPage: true });
      }
    }
    await page.goto(`${base}/password-reset/?preview_role=public`);
    assert.equal(await page.locator('input[type=email]').count(), 1);
    assert.deepEqual(errors, [], 'Unexpected browser errors');
    console.log('Browser checks passed: estimate approval, completion, receipt, recovery and responsive pages.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
