import {
  InstagramSocialLink,
  TikTokSocialLink,
} from "@/components/SocialLink";
import { SOCIAL_LINKS } from "@/lib/social-links";

const compactLight =
  "inline-flex h-9 w-9 items-center justify-center rounded-full border border-accent/25 bg-white/70 text-accent transition hover:border-accent hover:bg-accent hover:text-white";

const compactDark =
  "inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/25 bg-white/10 text-white transition hover:border-white/50 hover:bg-white/20";

export function EspaceSocialLinks({
  variant = "light",
}: {
  variant?: "light" | "dark";
}) {
  const className = variant === "dark" ? compactDark : compactLight;
  return (
    <div className="flex shrink-0 items-center gap-1.5" aria-label="Réseaux sociaux">
      <InstagramSocialLink
        href={SOCIAL_LINKS.instagram}
        className={className}
        iconClassName="h-4 w-4"
      />
      <TikTokSocialLink
        href={SOCIAL_LINKS.tiktok}
        className={className}
        iconClassName="h-4 w-4"
      />
    </div>
  );
}
