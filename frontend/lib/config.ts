export const USE_MOCK_API = process.env.NEXT_PUBLIC_USE_MOCK_API !== "false";
// Real API uses verified sessions; the default mock walkthrough needs no backend.
export const AUTH_ENABLED = process.env.NEXT_PUBLIC_ENABLE_AUTH === undefined
  ? !USE_MOCK_API
  : process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";

export const API_BASE_URL = AUTH_ENABLED
  ? "/api/v1"
  : process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
// Enable only after the deployment supplies a scoped V2 identity.
export const V2_WORKSPACE_ENABLED = AUTH_ENABLED
  ? process.env.NEXT_PUBLIC_ENABLE_V2_WORKSPACE === "true"
  : process.env.NEXT_PUBLIC_ENABLE_V2_WORKSPACE !== "false";
