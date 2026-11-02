const { execSync } = require("child_process");

// Stamped into the service worker's cache name (public/sw.js) so a deploy never
// serves pages cached by the previous one. CI/Vercel give a commit sha; locally use
// git, and fall back to the build time.
function buildId() {
  const fromEnv = process.env.NEXT_PUBLIC_BUILD_ID || process.env.VERCEL_GIT_COMMIT_SHA || process.env.GITHUB_SHA;
  if (fromEnv) return fromEnv.slice(0, 12);
  try {
    return execSync("git rev-parse --short=12 HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return Date.now().toString(36);
  }
}

const BUILD_ID = buildId();

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/agent",
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_BUILD_ID: BUILD_ID,
  },
};

module.exports = nextConfig;
