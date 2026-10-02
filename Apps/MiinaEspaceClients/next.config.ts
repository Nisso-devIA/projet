import path from "path";
import type { NextConfig } from "next";

const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=()",
  },
  { key: "X-DNS-Prefetch-Control", value: "off" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "X-Permitted-Cross-Domain-Policies", value: "none" },
  // Limite les fuites via formulaires / iframe sans casser Next (pas de script-src)
  {
    key: "Content-Security-Policy",
    value: "base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'",
  },
];

const noStoreAuthPages = [
  { key: "Cache-Control", value: "no-store, no-cache, must-revalidate, private" },
  { key: "Pragma", value: "no-cache" },
];

// HSTS posé par Nginx (évite les doublons)

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.join(__dirname),
  poweredByHeader: false,
  images: { unoptimized: true },
  serverExternalPackages: [
    "pdf-lib",
    "pdfjs-dist",
    "@napi-rs/canvas",
    "page-flip",
    "sharp",
  ],
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
      { source: "/", headers: noStoreAuthPages },
      { source: "/miina-admin/login", headers: noStoreAuthPages },
      { source: "/miina-admin/change-password", headers: noStoreAuthPages },
    ];
  },
};

export default nextConfig;
