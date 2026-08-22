export const LOCAL_E2E_BASE_URL = "http://127.0.0.1:4173";
export const E2E_BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? LOCAL_E2E_BASE_URL;
export const USE_LOCAL_E2E_SERVER = !process.env.PLAYWRIGHT_BASE_URL;
