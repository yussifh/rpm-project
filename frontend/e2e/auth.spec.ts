import { expect, test } from "@playwright/test";

/**
 * Self-contained: registers a brand-new patient rather than depending on
 * pre-seeded test data, so this suite can run against a freshly-migrated
 * database with no fixture setup step.
 */
function uniqueEmail() {
  return `e2e.patient.${Date.now()}@example.com`;
}

test.describe("Patient registration and login", () => {
  test("a new patient can register, then log in and reach their dashboard", async ({ page }) => {
    const email = uniqueEmail();

    await page.goto("/register");
    await page.getByLabel("Full name").fill("E2E Test Patient");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("SecurePass123");
    await page.getByLabel("Date of birth").fill("1990-01-01");
    await page.getByLabel("Gender").selectOption("female");
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page).toHaveURL(/\/login/);

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password").fill("SecurePass123");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/patient$/);
    await expect(page.getByText("Welcome back, E2E Test Patient")).toBeVisible();
  });

  test("shows an error for incorrect login credentials", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("nonexistent@example.com");
    await page.getByLabel("Password").fill("WrongPassword123");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByText("Incorrect email or password.")).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });

  test("an unauthenticated user is redirected away from a protected route", async ({ page }) => {
    await page.goto("/patient");
    await expect(page).toHaveURL(/\/login/);
  });
});
