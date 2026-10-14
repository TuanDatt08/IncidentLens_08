import { expect, test, type Page } from "@playwright/test";

const user = { id: "ui-user", email: "fixture@example.com", display_name: "Workspace User", roles: ["engineer", "admin"], is_active: true, must_change_password: false };

async function fixtures(page: Page) {
  await page.route("**/api/v1/**", route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/me")) return route.fulfill({ json: { user, csrf_token: "ui-fixture" } });
    if (path.endsWith("/admin/users")) return route.fulfill({ json: { items: [user], total: 1, limit: 20, offset: 0 } });
    return route.fulfill({ json: { items: [], total: 0, limit: 20, offset: 0 } });
  });
  await page.route("**/api/v2/**", route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/session")) return route.fulfill({ json: { subject: user.id, roles: ["Engineer"] } });
    return route.fulfill({ json: { items: [], next_cursor: null } });
  });
}

async function reflow(page: Page, name: string) {
  for (const width of [1440, 375, 320]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: test.info().outputPath(`${name}-${width}.png`), fullPage: true });
  }
}

test("login provides a clear entry and keyboard focus", async ({ page }) => {
  await page.route("**/api/v1/auth/me", route => route.fulfill({ status: 401, json: { error: { code: "AUTHENTICATION_REQUIRED", message: "Sign in" } } }));
  await page.goto("/login");
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await page.getByLabel("Email", { exact: true }).focus();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Password", { exact: true })).toBeFocused();
  await reflow(page, "login");
});

test("upload omits synchronization fields and retains multipart video and log", async ({ page }) => {
  await fixtures(page);
  await page.goto("/incidents/new");
  await expect(page.getByRole("button", { name: "Create Incident" })).toBeDisabled();
  await expect(page.getByText("Log/video offset (seconds)")).toHaveCount(0);
  await page.locator("#incident-video").setInputFiles({ name: "wrong.txt", mimeType: "text/plain", buffer: Buffer.from("invalid") });
  await expect(page.locator("#incident-video-error")).toContainText("MP4");
  await page.locator("#incident-video").setInputFiles("tests/e2e/fixtures/video.mp4");
  await page.locator("#incident-telemetry").setInputFiles({ name: "log.csv", mimeType: "text/csv", buffer: Buffer.from("time,speed\n0,1") });
  await expect(page.getByText("Optional synchronization metadata")).toHaveCount(0);
  await reflow(page, "upload");
  let received = "";
  await page.route("**/api/v1/incidents/upload", route => {
    received = route.request().postDataBuffer()?.toString() ?? "";
    return route.fulfill({ status: 503, json: { error: { code: "UNAVAILABLE", message: "Upload unavailable. Try again." } } });
  });
  await page.getByRole("button", { name: "Create Incident" }).click();
  await expect(page.locator(".upload-page [role=alert]")).toContainText("Upload unavailable");
  expect(received).toContain('name="video"');
  expect(received).toContain('name="log"');
  expect(received).not.toContain('name="sync_metadata"');
  expect(received).not.toContain('name="sync_offset_s"');
  await expect(page.getByRole("button", { name: "Create Incident" })).toBeEnabled();
});

test("users, password and recording pages reflow with working dialog focus", async ({ page }) => {
  await fixtures(page);
  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: "Users", exact: true })).toBeVisible();
  await reflow(page, "users");
  await page.getByRole("button", { name: "Create user", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Create user", exact: true })).toBeFocused();
  await page.goto("/change-password");
  await expect(page.getByLabel("New password", { exact: true })).toBeVisible();
  await reflow(page, "password");
  await page.goto("/recordings");
  await expect(page.getByText("No recordings yet", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Upload or resume" })).toBeDisabled();
  await reflow(page, "recordings");
  await page.goto("/recordings/REC-FIXTURE");
  await expect(page.getByRole("heading", { name: "Recording analysis", exact: true })).toBeVisible();
  await expect(page.getByText(/No candidates have been recorded/)).toBeVisible();
  await reflow(page, "recording-analysis");
});
