import { NextRequest, NextResponse } from "next/server";
import {
  ADMIN_COOKIE,
  ADMIN_MUST_CHANGE_COOKIE,
  AUTH_COOKIE,
  verifyAdminSession,
  verifySession,
} from "@/lib/auth";
import { adminEnabled, isAdminPath } from "@/lib/admin-config";

const ADMIN_BASE = "/miina-admin";
const PUBLIC_ORIGIN =
  "https://miinarecettesclients.xn--miina-ptisserie-9jb.fr";

/** Origin pour les redirects middleware.
 * Prod (next derrière nginx sur 127.0.0.1) → PUBLIC_ORIGIN.
 * Dev local → garder le host de la requête (sinon on est renvoyé en prod). */
function publicUrl(path: string, request: NextRequest) {
  const xfHost = request.headers.get("x-forwarded-host")?.split(",")[0]?.trim();
  const hostHeader = request.headers.get("host")?.trim() || "";
  const host = xfHost || hostHeader;
  const isLoopback =
    !host ||
    host.startsWith("127.") ||
    host.startsWith("localhost") ||
    host.startsWith("[::1]");

  if (isLoopback && process.env.NODE_ENV !== "production") {
    return new URL(path, `http://${host || "127.0.0.1:3003"}`);
  }

  const proto =
    request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim() || "https";
  const origin = isLoopback ? PUBLIC_ORIGIN : `${proto}://${host}`;
  return new URL(path, origin);
}

function redirectTo(path: string, request: NextRequest) {
  return NextResponse.redirect(publicUrl(path, request));
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (!adminEnabled() && isAdminPath(pathname, ADMIN_BASE)) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "Non trouvé" }, { status: 404 });
    }
    return new NextResponse(null, { status: 404 });
  }

  // Ancienne URL /admin → /miina-admin
  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    const dest = pathname.replace(/^\/admin/, ADMIN_BASE) || ADMIN_BASE;
    return redirectTo(dest, request);
  }

  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/brand") ||
    pathname.startsWith("/acces") ||
    pathname === "/favicon.ico" ||
    pathname === "/api/auth" ||
    pathname === "/api/admin/login"
  ) {
    return NextResponse.next();
  }

  if (pathname === `${ADMIN_BASE}/login`) {
    const adminOk = await verifyAdminSession(
      request.cookies.get(ADMIN_COOKIE)?.value,
    );
    const mustChange =
      request.cookies.get(ADMIN_MUST_CHANGE_COOKIE)?.value === "1";
    if (adminOk && mustChange) {
      return redirectTo(`${ADMIN_BASE}/change-password`, request);
    }
    if (adminOk) {
      return redirectTo(ADMIN_BASE, request);
    }
    return NextResponse.next();
  }

  if (pathname.startsWith(ADMIN_BASE) || pathname.startsWith("/api/admin")) {
    const adminOk = await verifyAdminSession(
      request.cookies.get(ADMIN_COOKIE)?.value,
    );
    if (!adminOk) {
      if (pathname.startsWith("/api/")) {
        return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
      }
      return redirectTo(`${ADMIN_BASE}/login`, request);
    }

    const mustChange =
      request.cookies.get(ADMIN_MUST_CHANGE_COOKIE)?.value === "1";
    const isChangePath =
      pathname === `${ADMIN_BASE}/change-password` ||
      pathname === "/api/admin/change-password" ||
      pathname === "/api/admin/logout";

    if (mustChange && !isChangePath) {
      if (pathname.startsWith("/api/")) {
        return NextResponse.json(
          { error: "Changement de mot de passe requis", code: "MUST_CHANGE" },
          { status: 403 },
        );
      }
      return redirectTo(`${ADMIN_BASE}/change-password`, request);
    }

    return NextResponse.next();
  }

  if (pathname === "/") {
    const ok = await verifySession(request.cookies.get(AUTH_COOKIE)?.value);
    if (ok) {
      return redirectTo("/espace", request);
    }
    return NextResponse.next();
  }

  if (pathname.startsWith("/espace") || pathname.startsWith("/api/moules") || pathname.startsWith("/api/entretien")) {
    const ok = await verifySession(request.cookies.get(AUTH_COOKIE)?.value);
    const adminOk = await verifyAdminSession(
      request.cookies.get(ADMIN_COOKIE)?.value,
    );
    if (!ok && !adminOk) {
      if (pathname.startsWith("/api/")) {
        return NextResponse.json({ error: "Non autorisé" }, { status: 401 });
      }
      return redirectTo("/", request);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/espace/:path*",
    "/acces",
    "/acces/:path*",
    "/admin",
    "/admin/:path*",
    "/miina-admin",
    "/miina-admin/:path*",
    "/api/admin/:path*",
    "/api/moules/:path*",
    "/api/entretien/:path*",
  ],
};
