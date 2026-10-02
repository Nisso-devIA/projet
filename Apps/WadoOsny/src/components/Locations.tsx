import Image from "next/image";
import type { ClubInfo } from "@/content/defaults";

type Props = {
  club: ClubInfo;
  /** Affiche le titre « Nous trouver » au-dessus du bloc */
  showTitle?: boolean;
};

export function Locations({ club, showTitle = false }: Props) {
  return (
    <div>
      {showTitle ? (
        <div className="mb-10 text-center">
          <h2 className="font-display text-3xl tracking-wide text-paper md:text-4xl">
            Nous trouver
          </h2>
          <div className="mx-auto mt-5 flex max-w-xl items-center gap-4">
            <span className="h-px flex-1 bg-crimson" aria-hidden />
            <ToriiIcon className="h-7 w-7 shrink-0 text-crimson-bright" />
            <span className="h-px flex-1 bg-crimson" aria-hidden />
          </div>
        </div>
      ) : null}

      <div className="grid items-stretch gap-0 overflow-hidden border border-line lg:grid-cols-2">
        <a
          href={club.mapLink}
          target="_blank"
          rel="noopener noreferrer"
          className="group relative min-h-[280px] bg-ink-lift lg:min-h-[420px]"
          aria-label="Ouvrir le plan d’accès dans Google Maps"
        >
          <Image
            src={club.mapImage}
            alt="Plan d’accès — Dojo municipal du Stade Christian Léon, Rue de Chars, Osny"
            fill
            className="object-cover object-center transition duration-500 group-hover:scale-[1.02]"
            sizes="(max-width: 1024px) 100vw, 50vw"
          />
          <span className="absolute bottom-4 left-4 rounded-sm bg-ink/80 px-3 py-1.5 text-xs font-medium text-paper backdrop-blur-sm transition group-hover:bg-crimson">
            Ouvrir dans Google Maps →
          </span>
        </a>

        <div className="flex flex-col justify-center gap-12 bg-ink-soft px-8 py-12 text-center md:px-12 md:py-16">
          {club.locations.map((loc) => (
            <article key={loc.name}>
              <h3 className="font-display text-xl leading-snug text-crimson-bright md:text-2xl">
                <a
                  href={loc.mapsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="transition hover:text-gold"
                >
                  {loc.name}
                </a>
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-paper-muted md:text-base">
                {loc.address}
                <br />
                {loc.city}
              </p>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}

function ToriiIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="currentColor"
      aria-hidden
      className={className}
    >
      <path d="M4 10h40v4H4z" />
      <path d="M8 6h32v4H8z" />
      <path d="M12 14h4v28h-4z" />
      <path d="M32 14h4v28h-4z" />
      <path d="M12 26h24v3H12z" />
    </svg>
  );
}
