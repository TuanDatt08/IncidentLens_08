import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { mockStore } from "../../services/mock-data";

// UI fixtures verify presentation and role visibility; auth.spec.ts verifies real RBAC.
for (const role of ["engineer", "reviewer", "admin"] as const) {
  test(`${role}: navigation, actual review states, header navigation and mobile reflow`, async ({ page }) => {
    const states = ["DRAFT", "IN_REVIEW", "APPROVED", "REJECTED"];
    const items = states.map((_, index) => ({
      incident_id: `INC-UI-${index}`, processing_status: "COMPLETED",
      created_at: "2026-10-12T00:00:00Z", incident_record: { scenario: "review_queue" },
    }));
    items.push({ incident_id: "INC-UI-PROCESSING", processing_status: "PROCESSING", created_at: "2026-10-12T00:00:00Z", incident_record: { scenario: "pending_analysis" } });
    await page.route("**/api/v1/**", async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname.endsWith("/auth/me")) return route.fulfill({ json: {
        csrf_token: "ui-fixture", user: { id: role, email: `${role}@example.com`, display_name: role, roles: [role], is_active: true, must_change_password: false },
      } });
      if (url.pathname === "/api/v1/incidents") {
        const selected = url.searchParams.get("review_status");
        const matching = selected ? items.filter((_, index) => states[index] === selected) : items;
        return route.fulfill({ json: { items: matching, total: matching.length, limit: 20, offset: 0,
          summary: { total: 5, processing: { COMPLETED: 4, PROCESSING: 1 }, reviews: { DRAFT: 1, IN_REVIEW: 1, APPROVED: 1, REJECTED: 1 } } } });
      }
      const match = url.pathname.match(/\/incidents\/INC-UI-(\d)\/report$/);
      if (match) return route.fulfill({ json: { ...mockStore.getDraft("RAV-18-0042"), incident_id: `INC-UI-${match[1]}`, review_status: states[Number(match[1])], version: 2 } });
      return route.fulfill({ status: 404, json: { error: { code: "NOT_FOUND", message: "Fixture unavailable" } } });
    });
    await page.goto("/incidents");
    const nav = page.getByRole("navigation", { name: "Workspace navigation" });
    await expect(nav.getByRole("link", { name: "Incidents", exact: true })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Create Incident", exact: true })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Upload video", exact: true })).toHaveCount(role === "engineer" ? 1 : 0);
    await expect(nav.getByRole("link", { name: "Users", exact: true })).toHaveCount(role === "admin" ? 1 : 0);
    await expect(page.locator("tbody").getByText("Reviewed", { exact: true })).toBeVisible();
    await expect(page.locator("tbody").getByText("No report yet", { exact: true })).toBeVisible();
    await expect(page.locator(".workspace-sidebar")).toHaveCount(0);
    await expect(page.locator(".workspace-topbar")).toBeVisible();
    await page.getByRole("button", { name: "In review 1", exact: true }).click();
    await expect(page.locator("tbody tr")).toHaveCount(1);
    await expect(page.locator("tbody").getByText("INC-UI-1", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "All 5", exact: true }).click();
    await page.getByRole("button", { name: "Account menu", exact: true }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("link", { name: "Change password", exact: true })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Account menu", exact: true })).toBeFocused();
    await expect(page.getByRole("link", { name: "Change password", exact: true })).toBeHidden();
    await page.getByRole("heading", { name: "Incidents", exact: true }).click();
    for (const width of [320, 375, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(page.locator(".workspace-shell")).toBeVisible();
      const geometry = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth, overflow: [...document.querySelectorAll("main *, aside *")].filter(el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 1; }).map(el => ({ tag: el.tagName, class: el.className, right: el.getBoundingClientRect().right })).slice(0, 12) }));
      await page.screenshot({ path: test.info().outputPath(`workspace-${role}-${width}.png`), fullPage: true });
      expect(geometry.scroll, JSON.stringify(geometry)).toBeLessThanOrEqual(geometry.width + 1);
    }
    await page.emulateMedia({ reducedMotion: "reduce" });
    expect(await page.locator(".workspace-shell").evaluate((el) => parseFloat(getComputedStyle(el).transitionDuration))).toBeLessThanOrEqual(0.00001);
    const row = page.locator("tbody tr").first();
    await expect(row.locator("a")).toHaveCount(1);
    await row.scrollIntoViewIfNeeded();
    const rowBounds = (await row.boundingBox())!;
    expect(await page.evaluate(({ x, y }) => document.elementFromPoint(x, y)?.closest("a")?.getAttribute("href"), { x: rowBounds.x + rowBounds.width - 8, y: rowBounds.y + rowBounds.height / 2 })).toBe("/incidents/INC-UI-0");
    await page.mouse.click(rowBounds.x + rowBounds.width - 8, rowBounds.y + rowBounds.height / 2);
    await expect(page).toHaveURL(/\/incidents\/INC-UI-0$/);
    await page.goto("/incidents");
    await page.setViewportSize({ width: 375, height: 900 });
    const card = page.locator(".incident-mobile-card").first();
    await expect(card).toBeVisible();
    await card.scrollIntoViewIfNeeded();
    const cardBounds = (await card.boundingBox())!;
    await page.mouse.click(cardBounds.x + cardBounds.width - 8, cardBounds.y + cardBounds.height - 8);
    await expect(page).toHaveURL(/\/incidents\/INC-UI-0$/);
  });
}

test("report sections keep unsaved edits, pause hidden media and expand Evidence", async ({ page }) => {
  // Exercise print content/focus without opening an OS print dialog in headless Edge.
  await page.addInitScript(() => { window.print = () => {
    if (window.top) window.top.document.documentElement.dataset.printedReport = document.body.innerText;
    window.dispatchEvent(new Event("afterprint"));
  }; });
  const id = "RAV-18-0042";
  const report = mockStore.getDraft(id)!;
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/auth/me")) return route.fulfill({ json: { csrf_token: "ui-fixture", user: { id: "engineer", email: "fixture@example.com", display_name: "Engineer", roles: ["engineer"], is_active: true, must_change_password: false } } });
    if (url.pathname.endsWith("/video/preview/status")) return route.fulfill({ json: { state: "ready" } });
    if (url.pathname.endsWith("/video")) {
      const media = readFileSync("tests/e2e/fixtures/video.mp4");
      const range = route.request().headers().range?.match(/^bytes=(\d+)-(\d*)$/);
      const start = range ? Number(range[1]) : 0;
      const end = range?.[2] ? Math.min(Number(range[2]), media.length - 1) : media.length - 1;
      return route.fulfill({ status: range ? 206 : 200, body: media.subarray(start, end + 1), contentType: "video/mp4", headers: { "Accept-Ranges": "bytes", "Content-Length": String(end - start + 1), ...(range ? { "Content-Range": `bytes ${start}-${end}/${media.length}` } : {}) } });
    }
    if (url.pathname.endsWith("/report")) return route.fulfill({ json: report });
    if (url.pathname.endsWith("/evidence")) return route.fulfill({ json: { items: [{ evidence_id: "E-UI-1", kind: "frame", uri: "fixture", sha256: "0".repeat(64), time_range_s: [-0.5, 0.5], tier: "core", bytes: 128, media_type: "image/png" }] } });
    if (url.pathname.endsWith("/audit")) return route.fulfill({ json: { items: [] } });
    if (url.pathname.endsWith("/review-context")) return route.fulfill({ json: { review_required: false, detection_state: "detected", summary: "Synthetic UI fixture.", model_output: { fixture: true }, warnings: [], time_basis: "video_seconds", alignment: "VERIFIED", points: Array.from({ length: 21 }, (_, index) => ({ time_s: index / 2, speed_kmh: 50 - index, brake_pct: index * 4, acceleration: -1 })), windows: [[3, 5]], telemetry_error: "No log supplied." } });
    if (url.pathname.endsWith("/analysis-coverage")) return route.fulfill({ json: { state: "available", time_basis: "video_seconds", duration_s: 10.07, sampled_timestamps_s: [0, .53, 1.05], sampled_frame_count: 3, telemetry_alignment: "UNKNOWN", limitations: ["Synthetic UI fixture.", "Synthetic UI fixture."] } });
    if (url.pathname === `/api/v1/incidents/${id}`) return route.fulfill({ json: mockStore.getIncident(id) });
    return route.fulfill({ status: 404, json: { error: { code: "NOT_FOUND", message: "Fixture unavailable" } } });
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`/incidents/${id}`);
  await page.getByRole("button", { name: "Report", exact: true }).click();
  await page.getByLabel("Summary text").fill("Unsaved section-switch draft");
  await page.getByRole("button", { name: "Inspect", exact: true }).click();
  await expect(page.getByLabel("Summary text")).toBeHidden();
  await expect(page.locator("video")).toHaveJSProperty("readyState", 4);
  const player = page.locator(".video-player");
  await page.getByRole("button", { name: "Mute video", exact: true }).click();
  await page.getByRole("button", { name: "Play video", exact: true }).click();
  await page.getByRole("button", { name: "Report", exact: true }).click();
  await expect(page.locator("video")).toBeVisible();
  await expect(page.getByLabel("Summary text")).toHaveValue("Unsaved section-switch draft");
  await page.getByRole("button", { name: "History", exact: true }).click();
  expect(await page.locator("video").evaluate((video: HTMLVideoElement) => video.paused)).toBe(true);
  await expect(page.getByLabel("Summary text")).toBeHidden();
  await page.getByRole("button", { name: "Inspect", exact: true }).click();
  const context = page.getByRole("region", { name: "Analysis & telemetry", exact: true });
  await expect(context.getByText("Synthetic UI fixture.", { exact: true })).toBeVisible();
  await expect(context.locator(".review-signal-stack > div")).toHaveCount(2);
  await page.locator("#telemetry-cursor").press("Home");
  await page.locator("#telemetry-cursor").press("ArrowRight");
  await expect.poll(() => page.locator("video").evaluate((video: HTMLVideoElement) => video.currentTime)).toBe(0.5);
  expect(await page.locator("video").evaluate((video: HTMLVideoElement) => video.paused)).toBe(true);
  expect(await page.locator(".review-pinned-video").evaluate(el => getComputedStyle(el).position)).toBe("sticky");
  await context.locator("summary").click();
  await expect(context.locator("pre")).toBeVisible();
  await page.getByRole("button", { name: "Customize colors" }).click();
  await page.getByRole("button", { name: "Ocean", exact: true }).click();
  await page.getByRole("button", { name: "Done", exact: true }).click();
  await expect(page.getByRole("button", { name: "Customize colors" })).toBeFocused();
  expect(await page.locator(".workspace-shell").evaluate(el => getComputedStyle(el).getPropertyValue("--workspace-primary"))).toBe("#70ead3");
  await page.getByRole("button", { name: "Customize colors" }).click();
  await page.getByRole("button", { name: "Galaxy", exact: true }).click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Workspace colors" })).toBeHidden();
  await page.getByRole("button", { name: "Export report", exact: true }).click();
  const preview = page.getByRole("dialog", { name: "Report preview", exact: true });
  await expect(preview).toBeVisible();
  await expect(preview.getByText(/Unsaved edits are excluded/)).toBeVisible();
  await preview.getByRole("button", { name: "JSON", exact: true }).click();
  await expect(preview.getByLabel("JSON preview")).not.toContainText("Unsaved section-switch draft");
  const jsonDownload = page.waitForEvent("download");
  await preview.getByRole("button", { name: "Download JSON", exact: true }).click();
  const jsonFile = await jsonDownload;
  expect(JSON.parse(readFileSync((await jsonFile.path())!, "utf8"))).toEqual(report);
  await preview.getByRole("button", { name: "DOCX", exact: true }).click();
  await expect(preview.getByLabel("Document preview")).toContainText(report.summary!);
  const docxDownload = page.waitForEvent("download");
  await preview.getByRole("button", { name: "Download DOCX", exact: true }).click();
  const docxFile = await docxDownload;
  await docxFile.saveAs(test.info().outputPath("report-export.docx"));
  expect(readFileSync((await docxFile.path())!).subarray(0, 4).toString("hex")).toBe("504b0304");
  await preview.getByRole("button", { name: "PDF", exact: true }).click();
  await expect(preview.getByRole("button", { name: "Print / Save PDF", exact: true })).toBeVisible();
  await page.screenshot({ path: test.info().outputPath("report-export-preview.png"), fullPage: true });
  await preview.getByRole("button", { name: "Print / Save PDF", exact: true }).click();
  await expect.poll(() => page.evaluate(() => document.documentElement.dataset.printedReport)).toContain(report.summary!);
  await expect(preview.getByRole("button", { name: "Print / Save PDF", exact: true })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(preview).toBeHidden();
  await expect(page.getByRole("button", { name: "Export report", exact: true })).toBeFocused();
  await page.screenshot({ path: test.info().outputPath("report-overview-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.getByRole("button", { name: "Report", exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  expect(await page.locator(".review-report .section-card").first().evaluate(el => getComputedStyle(el).backgroundColor)).toBe("rgb(16, 24, 41)");
  await page.getByRole("button", { name: "Save Changes", exact: true }).focus();
  const saveBounds = (await page.getByRole("button", { name: "Save Changes", exact: true }).boundingBox())!;
  expect(saveBounds.width).toBeGreaterThan(40);
  await page.getByRole("button", { name: "Inspect", exact: true }).click();
  await page.setViewportSize({ width: 375, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  expect((await page.locator(".video-player-stage").boundingBox())!.height).toBeLessThanOrEqual(900 * .6);
  await page.screenshot({ path: test.info().outputPath("report-overview-mobile.png"), fullPage: true });
  await player.screenshot({ path: test.info().outputPath("video-player-mobile.png") });
  await page.setViewportSize({ width: 320, height: 640 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  expect((await page.locator(".video-player-stage").boundingBox())!.height).toBeLessThanOrEqual(640 * .56 + 1);
  await page.getByRole("button", { name: "Export report", exact: true }).click();
  await expect(preview).toBeVisible();
  const mobilePreview = (await preview.boundingBox())!;
  expect(mobilePreview.width).toBeLessThanOrEqual(320);
  expect(mobilePreview.height).toBeLessThanOrEqual(640);
  await preview.getByRole("button", { name: "Close preview", exact: true }).click();
});
