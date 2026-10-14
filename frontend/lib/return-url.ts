export function safeReturnUrl(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u0020]/.test(value)) return "/incidents";
  try {
    const url = new URL(value, "https://local.invalid");
    if (url.origin !== "https://local.invalid" || !/^\/(incidents(?:\/|$)|admin\/users(?:\/|$))/.test(url.pathname)) return "/incidents";
    return url.pathname + url.search + url.hash;
  } catch { return "/incidents"; }
}
