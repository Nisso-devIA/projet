function Heart({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
      <path
        d="M12 20s-7-4.4-7-9.2C5 7.6 7.2 6 9.2 6c1.2 0 2.2.5 2.8 1.4C12.6 6.5 13.6 6 14.8 6 16.8 6 19 7.6 19 10.8 19 15.6 12 20 12 20z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function WelcomeCard() {
  return (
    <section
      aria-label="Bienvenue dans votre espace recettes"
      className="w-full max-w-xl rounded-[1.75rem] border border-ink/40 bg-[#f3e6d4] px-6 py-8 shadow-[0_10px_32px_rgba(59,42,36,0.14)] sm:px-10 sm:py-10"
    >
      <div className="mb-5 flex justify-center text-accent">
        <Heart className="h-5 w-5" />
      </div>

      <p className="font-script text-center text-[2.15rem] leading-tight text-ink sm:text-[2.55rem]">
        Bienvenue dans
      </p>
      <h1 className="font-display mt-2 text-center text-[1.85rem] leading-tight font-bold tracking-[0.04em] text-ink uppercase sm:text-[2.25rem]">
        Votre espace recettes
      </h1>

      <div className="my-4 flex items-center justify-center gap-3 text-accent">
        <span className="h-px w-16 border-t border-dashed border-accent/50" />
        <Heart className="h-3.5 w-3.5" />
        <span className="h-px w-16 border-t border-dashed border-accent/50" />
      </div>

      <p className="font-display mx-auto max-w-lg text-center text-[1.05rem] leading-relaxed font-bold text-ink sm:text-[1.15rem]">
        Cet espace a été créé avec soin et représente beaucoup de travail. Il
        est exclusivement réservé à mes clients Guy Demarle. 
        Je vous remercie de ne pas partager le lien de ce site ni son mot de passe afin que ces
        recettes restent votre petit privilège.
      </p>

      <div className="my-5 flex items-center justify-center gap-3 text-accent">
        <span className="h-px w-16 border-t border-dashed border-accent/50" />
        <Heart className="h-3.5 w-3.5" />
        <span className="h-px w-16 border-t border-dashed border-accent/50" />
      </div>

      <p className="font-script text-center text-[1.85rem] leading-tight text-ink sm:text-[2.25rem]">
        Merci pour votre confiance et bonne découverte&nbsp;!
      </p>

      <div className="mt-4 flex justify-center text-accent">
        <Heart className="h-5 w-5" />
      </div>
    </section>
  );
}
