import { expect, test } from "@playwright/test";

async function registerAndLogin(page: import("@playwright/test").Page) {
  const email = `e2e.nav.${Date.now()}@example.com`;

  await page.goto("/register");
  await page.getByLabel("Full name").fill("Nav Test Patient");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("SecurePass123");
  await page.getByLabel("Date of birth").fill("1990-01-01");
  await page.getByLabel("Gender").selectOption("male");
  await page.getByRole("button", { name: "Create account" }).click();

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("SecurePass123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/patient$/);
}

test.describe("Patient dashboard navigation", () => {
  test("sidebar links navigate to the correct sections", async ({ page }) => {
    await registerAndLogin(page);

    await page.getByRole("link", { name: "My Vitals" }).click();
    await expect(page).toHaveURL(/\/patient\/vitals/);

    await page.getByRole("link", { name: "Medications" }).click();
    await expect(page).toHaveURL(/\/patient\/medications/);

    await page.getByRole("link", { name: "Dashboard" }).click();
    await expect(page).toHaveURL(/\/patient$/);
  });

  test("logout returns to the login page and blocks further access", async ({ page }) => {
    await registerAndLogin(page);

    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/patient");
    await expect(page).toHaveURL(/\/login/);
  });
});
