/**
 * Resets the backend database to a clean, seeded state before the E2E suite
 * runs. Requires the backend to be started with ENVIRONMENT=test, which is
 * the only mode that exposes the /testing/reset endpoint (see
 * backend/app/api/routes/testing.py).
 */
const API_BASE_URL = process.env.E2E_API_BASE_URL || "http://localhost:8000/api/v1";

async function globalSetup() {
  const res = await fetch(`${API_BASE_URL}/testing/reset`, { method: "POST" });
  if (!res.ok) {
    throw new Error(
      `Failed to reset test database (${res.status}). Is the backend running with ENVIRONMENT=test?`
    );
  }
}

export default globalSetup;
