"use client";

import type { MouseEvent, ReactNode } from "react";
import { socialOpenPlan } from "@/lib/social-deep-link";

function isInstagramInApp() {
  return /Instagram/i.test(navigator.userAgent);
}

function isMobileUa(ua: string) {
  return /Android|iPhone|iPad|iPod/i.test(ua);
}

export function SocialLink({
  href,
  network,
  className,
  children,
}: {
  href: string;
  network: "instagram" | "tiktok";
  className: string;
  children: ReactNode;
}) {
  if (!href) {
    return (
      <span className={`${className} opacity-40`} title="Lien bientôt disponible">
        {children}
      </span>
    );
  }

  function openSocial(event: MouseEvent<HTMLAnchorElement>) {
    const ua = navigator.userAgent;
    const plan = socialOpenPlan(href, network, ua);

    if (!isMobileUa(ua)) return;

    if (isInstagramInApp() && network === "tiktok") {
      if (plan.appUrl && /Android/i.test(ua)) {
        event.preventDefault();
        window.location.href = plan.appUrl;
      }
      return;
    }

    if (!plan.appUrl) return;

    event.preventDefault();

    let openedApp = false;
    const markOpened = () => {
      openedApp = true;
    };
    window.addEventListener("pagehide", markOpened, { once: true });
    window.addEventListener("blur", markOpened, { once: true });
    document.addEventListener("visibilitychange", markOpened, { once: true });

    window.location.href = plan.appUrl;

    window.setTimeout(() => {
      window.removeEventListener("pagehide", markOpened);
      window.removeEventListener("blur", markOpened);
      document.removeEventListener("visibilitychange", markOpened);
      if (!openedApp && !document.hidden) {
        window.location.href = plan.webUrl;
      }
    }, 1200);
  }

  return (
    <a
      className={className}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onClick={openSocial}
    >
      {children}
    </a>
  );
}

function InstagramIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      aria-hidden
    >
      <rect x="3.1" y="3.1" width="17.8" height="17.8" rx="5" />
      <circle cx="12" cy="12" r="4.05" />
      <circle cx="17.4" cy="6.6" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}

function TikTokIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden>
      <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-5.2 1.74 2.89 2.89 0 0 1 2.31-4.64 2.93 2.93 0 0 1 .88.13V9.4a6.84 6.84 0 0 0-1-.05A6.33 6.33 0 0 0 5 20.1a6.34 6.34 0 0 0 10.86-4.43v-7a8.16 8.16 0 0 0 4.77 1.52v-3.4a4.85 4.85 0 0 1-1-.1z" />
    </svg>
  );
}

const iconClass =
  "inline-flex h-11 w-11 items-center justify-center rounded-full border border-accent/30 bg-white/80 text-accent transition hover:border-accent hover:bg-accent hover:text-white";

export function InstagramSocialLink({
  href,
  className = iconClass,
  iconClassName = "h-5 w-5",
}: {
  href: string;
  className?: string;
  iconClassName?: string;
}) {
  return (
    <SocialLink href={href} network="instagram" className={className}>
      <span className="sr-only">Instagram</span>
      <InstagramIcon className={iconClassName} />
    </SocialLink>
  );
}

export function TikTokSocialLink({
  href,
  className = iconClass,
  iconClassName = "h-5 w-5",
}: {
  href: string;
  className?: string;
  iconClassName?: string;
}) {
  return (
    <SocialLink href={href} network="tiktok" className={className}>
      <span className="sr-only">TikTok</span>
      <TikTokIcon className={iconClassName} />
    </SocialLink>
  );
}
