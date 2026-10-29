/** @type {import('next').NextConfig} */
export default {
  reactStrictMode: true,
  async rewrites() {
    // Browser calls relative /api/*; Next proxies server-side to FastAPI.
    // This keeps the API off the public internet and avoids CORS/secrets in the client.
    return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/api/:path*" }];
  },
};
