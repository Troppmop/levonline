import { test, expect } from "@playwright/test";
import {
  loginAs,
  TEST_ADMIN_EMAIL,
  TEST_ADMIN_PASSWORD,
  TEST_AV_BAYIT_EMAIL,
  TEST_AV_BAYIT_PASSWORD,
  TEST_RESIDENT_EMAIL,
  TEST_RESIDENT_PASSWORD,
} from "./fixtures";

// Uses the raw Playwright `test` (not the auto-login fixture from
// fixtures.ts) since each case here needs to log in as a different role.

test("admin sees the staff dashboard", async ({ page }) => {
  await loginAs(page, TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD);
  await page.waitForURL("**/dashboard");
  await expect(page.getByRole("heading", { name: "Live Dashboard" })).toBeVisible();
});

test(
  "admin sees the bottom nav on a mobile viewport, not on desktop",
  { tag: "@mobile-only" },
  async ({ page, isMobile }) => {
    await loginAs(page, TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD);
    await page.waitForURL("**/dashboard");
    const nav = page.getByRole("navigation", { name: "Primary" });
    // The bottom nav is deliberately `sm:hidden` — a fixed bar makes sense
    // for one-thumb mobile navigation but would just be clutter on desktop,
    // where the existing top nav already shows every link at once.
    if (isMobile) {
      await expect(nav).toBeVisible();
    } else {
      await expect(nav).toBeHidden();
    }
  }
);

test("resident is routed to their own mobile portal, not the staff shell", async ({ page }) => {
  await loginAs(page, TEST_RESIDENT_EMAIL, TEST_RESIDENT_PASSWORD);
  await page.waitForURL("**/r/home");
  await expect(page.getByText("Welcome back,")).toBeVisible();

  // Residents must never reach staff-only routes, even by direct navigation.
  await page.goto("/residents");
  await page.waitForURL("**/r/home");
});

test("resident can toggle their own home/away status", async ({ page }) => {
  await loginAs(page, TEST_RESIDENT_EMAIL, TEST_RESIDENT_PASSWORD);
  await page.waitForURL("**/r/home");

  const toggleButton = page.getByRole("button", { name: /Mark (Home|Away)/ });
  await expect(toggleButton).toBeVisible();
  await toggleButton.click();
  // Status text renders lowercase from the API ("home"/"away") and is only
  // visually capitalized via CSS, so match case-insensitively.
  await expect(page.getByText(/^(home|away)$/i)).toBeVisible();
});

test("av/eim bayit can invite their assigned resident to a meal", async ({ page }) => {
  await loginAs(page, TEST_AV_BAYIT_EMAIL, TEST_AV_BAYIT_PASSWORD);
  await page.waitForURL("**/dashboard");

  await page.goto("/meals");
  await expect(page.getByText("Invite Your Assigned Soldiers")).toBeVisible();
  await expect(page.getByRole("option", { name: "E2E Resident" })).toBeAttached();
});
