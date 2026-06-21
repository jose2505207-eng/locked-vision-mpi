// Frontend Sentry init — OPTIONAL, fail-soft, never breaks the build.
//
// Active only when VITE_ENABLE_SENTRY=true and VITE_SENTRY_DSN is set, AND
// @sentry/react is installed (`npm i @sentry/react`). If anything is missing it
// logs once and the app runs normally. The dynamic import uses a variable
// specifier + @vite-ignore so a missing package can't fail `npm run build`.
export async function initSentry() {
  const enabled =
    String(import.meta.env.VITE_ENABLE_SENTRY || "").toLowerCase() === "true";
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!enabled || !dsn) {
    console.debug("[sentry] frontend inactive (flag off or DSN missing)");
    return false;
  }
  try {
    const pkg = "@sentry/react";
    const Sentry = await import(/* @vite-ignore */ pkg);
    Sentry.init({ dsn, tracesSampleRate: 0.2, environment: "demo" });
    console.debug("[sentry] frontend initialized");
    return true;
  } catch (e) {
    console.warn("[sentry] frontend init skipped (soft):", e?.message || e);
    return false;
  }
}
