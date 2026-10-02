import Link from "next/link";

type Props = {
  eyebrow?: string;
  title: string;
  description?: string;
  cta?: { href: string; label: string };
  dark?: boolean;
};

export function PageHero({ eyebrow, title, description, cta, dark = true }: Props) {
  return (
    <section
      className={`relative overflow-hidden border-b border-line pt-28 pb-16 md:pt-36 md:pb-20 ${
        dark ? "hero-gradient" : "bg-ink-soft"
      }`}
    >
      <div className="grain absolute inset-0" aria-hidden />
      <div className="relative z-[2] mx-auto max-w-7xl px-5 md:px-8">
        {eyebrow ? (
          <p className="animate-rise text-xs font-semibold uppercase tracking-[0.28em] text-gold">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="animate-rise-delay-1 mt-4 max-w-3xl font-display text-4xl leading-[1.05] tracking-tight text-paper md:text-6xl">
          {title}
        </h1>
        <span
          className="underline-draw mt-5 block h-px w-24 bg-crimson-bright"
          aria-hidden
        />
        {description ? (
          <p className="animate-rise-delay-2 mt-6 max-w-2xl text-base leading-relaxed text-paper-muted md:text-lg">
            {description}
          </p>
        ) : null}
        {cta ? (
          <Link
            href={cta.href}
            className="animate-rise-delay-3 mt-8 inline-flex rounded-sm bg-crimson px-5 py-3 text-sm font-medium text-paper transition hover:bg-crimson-bright"
          >
            {cta.label}
          </Link>
        ) : null}
      </div>
    </section>
  );
}
