"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import {
  nav,
  navItemIsActive,
  site,
  type NavItem,
} from "@/content/site";

export function Header({ brandName = site.name }: { brandName?: string }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [mobileSection, setMobileSection] = useState<string | null>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpen(false);
    setMobileSection(null);
  }, [pathname]);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-colors duration-300 ${
        scrolled || open
          ? "border-b border-line bg-ink/90 backdrop-blur-md"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-3 md:px-8">
        <Link href="/" className="group flex items-center gap-3">
          <Image
            src="/images/logo.png"
            alt={brandName}
            width={48}
            height={48}
            className="h-11 w-11 transition-transform duration-500 group-hover:rotate-6"
            priority
          />
          <span className="font-display text-lg tracking-tight text-paper md:text-xl">
            {brandName}
          </span>
        </Link>

        <nav className="hidden items-center gap-0.5 xl:flex">
          {nav.map((item) => (
            <DesktopNavItem
              key={item.label}
              item={item}
              pathname={pathname}
            />
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/contact"
            className="hidden rounded-sm bg-crimson px-4 py-2 text-sm font-medium text-paper transition hover:bg-crimson-bright sm:inline-flex"
          >
            Nous rejoindre
          </Link>
          <button
            type="button"
            aria-label={open ? "Fermer le menu" : "Ouvrir le menu"}
            aria-expanded={open}
            className="inline-flex h-10 w-10 items-center justify-center rounded-sm border border-line text-paper xl:hidden"
            onClick={() => setOpen((v) => !v)}
          >
            <span className="sr-only">Menu</span>
            <span className="flex w-5 flex-col gap-1.5">
              <span
                className={`h-px w-full bg-paper transition ${open ? "translate-y-[7px] rotate-45" : ""}`}
              />
              <span
                className={`h-px w-full bg-paper transition ${open ? "opacity-0" : ""}`}
              />
              <span
                className={`h-px w-full bg-paper transition ${open ? "-translate-y-[7px] -rotate-45" : ""}`}
              />
            </span>
          </button>
        </div>
      </div>

      {open ? (
        <div className="border-t border-line bg-ink/95 px-5 py-4 xl:hidden">
          <nav className="flex flex-col">
            {nav.map((item) => {
              if ("href" in item) {
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="border-b border-line py-3 font-display text-lg uppercase tracking-wide text-paper"
                  >
                    {item.label}
                  </Link>
                );
              }

              const expanded = mobileSection === item.label;
              return (
                <div key={item.label} className="border-b border-line">
                  <button
                    type="button"
                    className="flex w-full items-center justify-between py-3 font-display text-lg uppercase tracking-wide text-paper"
                    aria-expanded={expanded}
                    onClick={() =>
                      setMobileSection(expanded ? null : item.label)
                    }
                  >
                    {item.label}
                    <Chevron open={expanded} />
                  </button>
                  {expanded ? (
                    <div className="mb-3 overflow-hidden rounded-sm border border-line bg-ink-lift">
                      {item.children.map((child) => (
                        <Link
                          key={child.href}
                          href={child.href}
                          className="block border-b border-line px-4 py-3 text-sm font-semibold uppercase tracking-wider text-paper-muted last:border-b-0 transition hover:bg-ink-soft hover:text-paper"
                        >
                          {child.label}
                        </Link>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </nav>
        </div>
      ) : null}
    </header>
  );
}

function DesktopNavItem({
  item,
  pathname,
}: {
  item: NavItem;
  pathname: string;
}) {
  const active = navItemIsActive(item, pathname);
  const [open, setOpen] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const menuId = useId();

  const clearClose = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  };

  const scheduleClose = () => {
    clearClose();
    closeTimer.current = setTimeout(() => setOpen(false), 120);
  };

  if ("href" in item) {
    return (
      <Link
        href={item.href}
        className={`relative px-2.5 py-2 text-[13px] font-semibold uppercase tracking-wide transition-colors ${
          active ? "text-paper" : "text-paper-muted hover:text-paper"
        }`}
      >
        {item.label}
        {active ? (
          <span className="absolute inset-x-2.5 -bottom-0.5 h-px bg-crimson-bright" />
        ) : null}
      </Link>
    );
  }

  return (
    <div
      className="relative"
      onMouseEnter={() => {
        clearClose();
        setOpen(true);
      }}
      onMouseLeave={scheduleClose}
      onFocus={() => {
        clearClose();
        setOpen(true);
      }}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) {
          setOpen(false);
        }
      }}
    >
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={menuId}
        className={`relative inline-flex items-center gap-1.5 px-2.5 py-2 text-[13px] font-semibold uppercase tracking-wide transition-colors ${
          active || open ? "text-paper" : "text-paper-muted hover:text-paper"
        }`}
        onClick={() => setOpen((v) => !v)}
      >
        {item.label}
        <Chevron open={open} />
        {active ? (
          <span className="absolute inset-x-2.5 -bottom-0.5 h-px bg-crimson-bright" />
        ) : null}
      </button>

      <div
        id={menuId}
        role="menu"
        className={`absolute left-0 top-full z-50 min-w-[13.5rem] origin-top pt-2 transition ${
          open
            ? "pointer-events-auto scale-100 opacity-100"
            : "pointer-events-none scale-95 opacity-0"
        }`}
      >
        <div className="overflow-hidden rounded-sm border border-line bg-ink-lift/95 shadow-2xl shadow-black/50 backdrop-blur-md">
          {item.children.map((child) => {
            const childActive =
              pathname === child.href ||
              pathname.startsWith(`${child.href}/`);
            return (
              <Link
                key={child.href}
                href={child.href}
                role="menuitem"
                className={`block border-b border-line px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] last:border-b-0 transition ${
                  childActive
                    ? "bg-ink-soft text-gold"
                    : "text-paper-muted hover:bg-ink-soft hover:text-paper"
                }`}
              >
                {child.label}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 12 12"
      className={`h-2.5 w-2.5 transition-transform ${open ? "rotate-180" : ""}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <path d="M2 4l4 4 4-4" />
    </svg>
  );
}
