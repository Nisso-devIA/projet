function LeafSprig() {
  return (
    <svg viewBox="0 0 28 28" className="h-6 w-6 shrink-0 text-[#b08a68]" fill="none" aria-hidden>
      <path
        d="M6 22c6-1 10-6 14-16"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
      <path
        d="M10 18c-1.2-3.2 1-5.5 3.2-5.2M14 14c-.4-3 1.8-4.8 3.6-4.2M17.5 10c-.2-2.2 1.2-3.6 2.6-3.2"
        stroke="currentColor"
        strokeWidth="1.15"
        strokeLinecap="round"
      />
      <path
        d="M8.5 12.5c.7-1.1 1.8-1.4 2.4-.6"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinecap="round"
      />
    </svg>
  );
}

function TinyHeart({ className = "h-2.5 w-2.5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} fill="none" aria-hidden>
      <path
        d="M8 13.5S3 10.2 3 6.8C3 5 4.4 4 5.7 4c.9 0 1.6.4 2.1 1.1C8.3 4.4 9 4 9.9 4 11.2 4 12.6 5 12.6 6.8 12.6 10.2 8 13.5 8 13.5z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

type Props = {
  href: string;
  label: string;
  /** Lien FlipHTML5 externe ; false = lecteur interne */
  external?: boolean;
};

export function VoirRecettesButton({ href, label, external = true }: Props) {
  return (
    <a
      href={href}
      {...(external
        ? { target: "_blank", rel: "noopener noreferrer" }
        : {})}
      aria-label={label}
      className="group inline-flex h-9 w-[12.25rem] items-center justify-between gap-1 rounded-full border border-[#c4a484] bg-[#fffaf4] px-2 shadow-[inset_0_0_0_1px_#c4a484] transition hover:-translate-y-0.5 sm:h-10 sm:w-[13rem] sm:px-2.5"
    >
      <span className="relative flex w-7 shrink-0 items-center justify-center text-[#b08a68]">
        <LeafSprig />
        <span className="absolute top-0 right-0.5">
          <TinyHeart className="h-2 w-2" />
        </span>
      </span>

      <span className="font-display flex-1 text-center text-[0.62rem] font-semibold tracking-[0.06em] text-[#5c4033] uppercase sm:text-[0.68rem]">
        Voir les recettes
      </span>

      <span className="relative flex w-8 shrink-0 items-center justify-center">
        <span className="grid h-6 w-6 place-items-center rounded-full bg-[#d4b496] text-[#5c4033] transition group-hover:bg-[#c9a788]">
          <svg viewBox="0 0 12 12" className="h-3 w-3" fill="none" aria-hidden>
            <path
              d="M4 2.5 L8 6 L4 9.5"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span className="absolute -right-0.5 -bottom-0.5 text-[#b08a68]">
          <TinyHeart className="h-2 w-2" />
        </span>
      </span>
    </a>
  );
}
