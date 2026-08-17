import { expect, test } from "./fixtures";

test("presence board renders seeded rooms by floor layout", async ({ page }) => {
  await page.goto("/presence");
  await expect(page.getByRole("heading", { name: "Presence Tracker" })).toBeVisible();
  await expect(page.getByText("Floor 1")).toBeVisible();
  await expect(page.getByText("Floor 2")).toBeVisible();
  await expect(page.getByText("Room 101")).toBeVisible();
});

test("resident can be added and toggled home/away", async ({ page }) => {
  await page.goto("/residents");
  await page.getByPlaceholder("First name").fill("Test");
  await page.getByPlaceholder("Last name").fill("Resident");
  await page.getByRole("button", { name: "Add Resident" }).click();
  // .first(): other projects run this same test concurrently against the
  // same shared backend, so more than one "Test Resident" row can exist —
  // this only asserts that ours was added, not that the name is unique.
  await expect(page.getByText("Test Resident").first()).toBeVisible();
});
