import { test as base, expect } from "@playwright/test";

export const TEST_ADMIN_EMAIL = "e2e-admin@lev.org";
export const TEST_ADMIN_PASSWORD = "e2e-test-password";
export const TEST_AV_BAYIT_EMAIL = "e2e-avbayit@lev.org";
export const TEST_AV_BAYIT_PASSWORD = "e2e-test-password";
export const TEST_RESIDENT_EMAIL = "e2e-resident@lev.org";
export const TEST_RESIDENT_PASSWORD = "e2e-test-password";

async function loginAs(page: import("@playwright/test").Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

export const test = base.extend({
  page: async ({ page }, use) => {
    await loginAs(page, TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD);
    await page.waitForURL("**/dashboard");
    await use(page);
  },
});

export { expect, loginAs };
