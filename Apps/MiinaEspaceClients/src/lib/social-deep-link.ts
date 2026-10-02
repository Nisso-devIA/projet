/** Extrait un pseudo depuis une URL Instagram / TikTok. */
export function socialUsername(
  url: string,
  network: "instagram" | "tiktok",
): string | null {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.replace(/^www\./, "").toLowerCase();
    if (network === "instagram" && !host.includes("instagram.com")) return null;
    if (network === "tiktok" && !host.includes("tiktok.com")) return null;

    const parts = parsed.pathname.split("/").filter(Boolean);
    if (!parts.length) return null;
    let user = parts[0] === "_u" ? parts[1] : parts[0];
    if (!user) return null;
    user = decodeURIComponent(user).replace(/^@/, "");
    if (
      !user ||
      user === "share" ||
      user === "reel" ||
      user === "p" ||
      user === "video"
    ) {
      return null;
    }
    return user;
  } catch {
    return null;
  }
}

export type SocialOpenPlan = {
  appUrl?: string;
  webUrl: string;
};

export function socialOpenPlan(
  url: string,
  network: "instagram" | "tiktok",
  ua: string,
): SocialOpenPlan {
  const user = socialUsername(url, network);
  const isAndroid = /Android/i.test(ua);
  const isIOS = /iPhone|iPad|iPod/i.test(ua);

  if (network === "instagram") {
    const webUrl = user ? `https://www.instagram.com/_u/${user}/` : url;
    if ((isAndroid || isIOS) && user) {
      return {
        appUrl: `instagram://user?username=${encodeURIComponent(user)}`,
        webUrl,
      };
    }
    return { webUrl };
  }

  const webUrl = user ? `https://www.tiktok.com/@${user}` : url;
  if (isAndroid && user) {
    const fallback = encodeURIComponent(webUrl);
    return {
      appUrl: `intent://www.tiktok.com/@${user}#Intent;scheme=https;package=com.zhiliaoapp.musically;S.browser_fallback_url=${fallback};end`,
      webUrl,
    };
  }
  return { webUrl };
}
