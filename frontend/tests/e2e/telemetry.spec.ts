import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { mockStore } from "../../services/mock-data";

const id = "RAV-18-0042";
const media = readFileSync("tests/e2e/fixtures/video.mp4");
const chart = (start = 0) => ({ state: "available", time_basis: "video_seconds", alignment: "VERIFIED", duration_s: start + 10, row_count: 11, downsampled: false, message: null, signals: [
  { key: "speed", label: "Speed", unit: "m/s", samples: Array.from({ length: 11 }, (_, i) => ({ time_s: start + i, value: i === 6 ? null : 10 + i })) },
  { key: "brake", label: "Brake", unit: null, samples: Array.from({ length: 11 }, (_, i) => ({ time_s: start + i, value: i === 5 ? 1 : 0 })) },
] });

async function videoResponse(route: import("@playwright/test").Route) {
  const range = route.request().headers().range;
  const match = range?.match(/bytes=(\d+)-(\d*)/);
  const start = match ? Number(match[1]) : 0;
  const end = match?.[2] ? Math.min(Number(match[2]), media.length - 1) : media.length - 1;
  await route.fulfill({ status: match ? 206 : 200, body: media.subarray(start, end + 1), headers: { "Content-Type": "video/mp4", "Accept-Ranges": "bytes", ...(match ? { "Content-Range": `bytes ${start}-${end}/${media.length}` } : {}) } });
}

test("incident context displays verified telemetry and supports keyboard selection", async ({ page }) => {
  const points = Array.from({ length: 11 }, (_, i) => ({ time_s: i, speed_kmh: 10 + i, brake_pct: i === 5 ? 80 : 0, acceleration: -1 }));
  await page.route("**/api/v1/**", route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/me")) return route.fulfill({ json: { csrf_token: "fixture", user: { id: "engineer", roles: ["engineer"], email: "fixture@example.com", display_name: "Engineer", is_active: true, must_change_password: false } } });
    if (path.endsWith("/video")) return videoResponse(route);
    if (path.endsWith("/review-context")) return route.fulfill({ json: { review_required: false, detection_state: "detected", summary: "Synthetic context", model_output: {}, warnings: [], time_basis: "video_seconds", alignment: "VERIFIED", points, windows: [[4, 6]], telemetry_error: null } });
    if (path.endsWith("/report")) return route.fulfill({ json: mockStore.getDraft(id) });
    if (path === `/api/v1/incidents/${id}`) return route.fulfill({ json: mockStore.getIncident(id) });
    return route.fulfill({ json: { items: [] } });
  });
  await page.goto(`/incidents/${id}`);
  await expect(page.locator("video")).toHaveJSProperty("readyState", 4);
  const cursor = page.getByLabel("Chọn thời điểm trên biểu đồ", { exact: true });
  await expect(cursor).toHaveValue("5");
  await cursor.focus();
  await page.keyboard.press("ArrowRight");
  await expect(cursor).toHaveValue("6");
  await page.getByRole("button", { name: "Xem video tại 6.00s" }).click();
  await expect.poll(() => page.locator("video").evaluate((video: HTMLVideoElement) => video.currentTime)).toBe(6);
  await page.setViewportSize({ width: 320, height: 900 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: test.info().outputPath("context-telemetry-mobile.png"), fullPage: true });
});

test("unverified context shows an explicit telemetry limitation and no seek controls", async ({ page }) => {
  await page.route("**/api/v1/**", route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/me")) return route.fulfill({ json: { csrf_token: "fixture", user: { id: "engineer", display_name: "Engineer", email: "fixture@example.com", roles: ["engineer"], is_active: true, must_change_password: false } } });
    if (path.endsWith("/review-context")) return route.fulfill({ json: { review_required: false, detection_state: null, summary: null, model_output: {}, warnings: [], time_basis: "video_seconds", alignment: "UNKNOWN", points: [], windows: [], telemetry_error: "Unverified telemetry alignment." } });
    if (path.endsWith("/report")) return route.fulfill({ json: mockStore.getDraft(id) });
    if (path === `/api/v1/incidents/${id}`) return route.fulfill({ json: mockStore.getIncident(id) });
    return route.fulfill({ json: { items: [] } });
  });
  await page.goto(`/incidents/${id}`);
  await expect(page.getByText("Unverified telemetry alignment.", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Chọn thời điểm trên biểu đồ", { exact: true })).toHaveCount(0);
});

test("recording chart accounts for a nonzero approved clip start", async ({ page }) => {
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/auth/me")) return route.fulfill({ json: { csrf_token: "fixture", user: { id: "engineer", display_name: "Engineer", email: "fixture@example.com", roles: ["engineer"], is_active: true, must_change_password: false } } });
    if (path.endsWith("/session")) return route.fulfill({ json: { subject: "engineer", roles: ["Engineer"] } });
    if (path.endsWith("/telemetry")) return route.fulfill({ json: chart(30) });
    if (path.endsWith("/media")) return videoResponse(route);
    if (path.endsWith("/evidence")) return route.fulfill({ json: { items: [{ evidence_id: "clip", source: "VIDEO", start_s: 30, end_s: 40, media_type: "video/mp4", privacy_state: "APPROVED", privacy_validation: "PASSED", media_url: "/recordings/R1/evidence/clip/media" }] } });
    if (path === "/api/v2/reports/P1") return route.fulfill({ json: { recording_id: "R1", candidate_id: "C1", report_id: "P1", version: 1, provenance: {}, submitted_by: null, analysis: { schema_version: "2.0", incident_detected: true, time_basis: "video_seconds", event_type: "HARD_BRAKING", window: { start_s: 32, critical_s: 35, end_s: 38 }, summary: "Synthetic chart fixture", timeline: [], factors: [], unknowns: [], review_status: "DRAFT" } } });
    return route.fulfill({ json: { items: [] } });
  });
  await page.goto("/reports/P1");
  const timeline = page.getByRole("slider", { name: "Log timeline" });
  await expect(timeline).toBeEnabled();
  await expect(timeline).toHaveAttribute("min", "30");
  await page.locator("video").evaluate((video: HTMLVideoElement) => { video.currentTime = 3; video.dispatchEvent(new Event("timeupdate")); });
  await expect(timeline).toHaveValue("33");
  await timeline.fill("35");
  await expect.poll(() => page.locator("video").evaluate((video: HTMLVideoElement) => video.currentTime)).toBe(5);
  await expect(timeline).toHaveValue("35");
});
