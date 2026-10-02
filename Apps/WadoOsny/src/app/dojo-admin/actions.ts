"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import {
  clearAdminCookie,
  issueAdminSession,
  isAdminLoggedIn,
} from "@/lib/admin-auth";
import { passwordPolicyError } from "@/lib/admin-constants";
import { adminPath } from "@/lib/admin-paths";
import { sessionSecretReady } from "@/lib/admin-session";
import {
  isPasswordExpired,
  passwordMatches,
  updateAdminPassword,
} from "@/lib/admin-store";
import { isUploadSrc, removeUploadSrc, saveImageUpload } from "@/lib/image-upload";
import {
  clearLoginAttempts,
  clientIpFromHeaders,
  consumeLoginAttempt,
  isProduction,
  publicError,
  sanitizeHref,
} from "@/lib/security";
import {
  getClub,
  getEvents,
  getGallery,
  getInstructors,
  getPricing,
  getSchedules,
  saveClub,
  saveEvents,
  saveGallery,
  saveInstructors,
  savePricing,
  saveSchedules,
} from "@/content/club-data";
import type {
  AdultGroup,
  ClubEvent,
  ClubInfo,
  GalleryItem,
  Instructor,
  KidsGroup,
  PricingPlan,
} from "@/content/defaults";
import { GALLERY_CATEGORIES } from "@/content/defaults";

function revalidatePublic() {
  revalidatePath("/", "layout");
  for (const p of [
    "/",
    "/calendrier",
    "/mediatheque",
    "/horaires",
    "/tarifs",
    "/instructeurs",
    "/contact",
  ]) {
    revalidatePath(p);
  }
}

export async function loginAdmin(
  _prev: { error?: string } | null,
  formData: FormData,
) {
  if (!sessionSecretReady()) {
    return {
      error: isProduction()
        ? "Configuration serveur incomplète (ADMIN_SECRET)."
        : "Ajoutez ADMIN_SECRET ou ADMIN_PASSWORD dans le fichier .env.",
    };
  }

  const ip = clientIpFromHeaders(await headers());
  const limit = await consumeLoginAttempt(ip);
  if (!limit.ok) {
    return {
      error: `Trop d’essais. Réessayez dans ${limit.retryMinutes} min.`,
    };
  }

  const password = String(formData.get("password") ?? "");
  try {
    if (!(await passwordMatches(password))) {
      return { error: "Mot de passe incorrect." };
    }
  } catch (error) {
    return { error: publicError(error, "Connexion impossible.") };
  }

  await clearLoginAttempts(ip);
  await issueAdminSession();
  if (await isPasswordExpired()) {
    redirect(adminPath("/mot-de-passe"));
  }
  redirect(adminPath());
}

export async function logoutAdmin() {
  await clearAdminCookie();
  redirect(adminPath("/login"));
}

async function guardLoggedIn() {
  if (!(await isAdminLoggedIn())) redirect(adminPath("/login"));
}

async function guard() {
  await guardLoggedIn();
  if (await isPasswordExpired()) redirect(adminPath("/mot-de-passe"));
}

export async function changeAdminPassword(
  _prev: { error?: string } | null,
  formData: FormData,
) {
  await guardLoggedIn();
  const current = String(formData.get("currentPassword") ?? "");
  const next = String(formData.get("newPassword") ?? "");
  const confirm = String(formData.get("confirmPassword") ?? "");

  try {
    if (!(await passwordMatches(current))) {
      return { error: "Le mot de passe actuel est incorrect." };
    }
    const policy = passwordPolicyError(next);
    if (policy) return { error: policy };
    if (next !== confirm) {
      return { error: "La confirmation ne correspond pas." };
    }
    if (next === current) {
      return { error: "Choisissez un mot de passe différent de l’actuel." };
    }
    await updateAdminPassword(next);
    await clearAdminCookie();
  } catch (error) {
    return { error: publicError(error, "Modification impossible.") };
  }
  redirect(adminPath("/login?pwd=1"));
}

function newId(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}`;
}

export async function saveEventAction(
  _prev: { error?: string } | null,
  formData: FormData,
) {
  await guard();
  try {
    const id = String(formData.get("id") ?? "").trim() || newId("ev");
    const event: ClubEvent = {
      id,
      title: String(formData.get("title") ?? "").trim(),
      date: String(formData.get("date") ?? "").trim(),
      time: String(formData.get("time") ?? "").trim(),
      place: String(formData.get("place") ?? "").trim(),
      description: String(formData.get("description") ?? "").trim(),
    };
    if (!event.title || !event.date) {
      throw new Error("Titre et date obligatoires.");
    }
    const events = await getEvents();
    const idx = events.findIndex((e) => e.id === id);
    if (idx >= 0) events[idx] = event;
    else events.push(event);
    await saveEvents(events);
    revalidatePublic();
  } catch (error) {
    return { error: publicError(error, "Enregistrement impossible.") };
  }
  redirect(adminPath("/evenements?ok=1"));
}

export async function deleteEventAction(formData: FormData) {
  await guard();
  const id = String(formData.get("id") ?? "");
  const events = await getEvents();
  await saveEvents(events.filter((e) => e.id !== id));
  revalidatePublic();
  redirect(adminPath("/evenements"));
}

export async function addGalleryItemAction(
  _prev: { error?: string } | null,
  formData: FormData,
) {
  await guard();
  try {
    const file = formData.get("file");
    if (!(file instanceof File) || !file.size) {
      throw new Error("Choisissez une image.");
    }
    const alt = String(formData.get("alt") ?? "").trim() || "Photo du club";
    const category = String(formData.get("category") ?? "Cours").trim();
    if (!(GALLERY_CATEGORIES as readonly string[]).includes(category)) {
      throw new Error("Catégorie invalide.");
    }
    const id = newId("g");
    const src = await saveImageUpload(file, "gallery", id);
    const items = await getGallery();
    items.unshift({ id, src, alt, category });
    await saveGallery(items);
    revalidatePublic();
  } catch (error) {
    return { error: publicError(error, "Ajout impossible.") };
  }
  redirect(adminPath("/mediatheque?ok=1"));
}

export async function updateGalleryItemAction(
  _prev: { error?: string } | null,
  formData: FormData,
) {
  await guard();
  try {
    const id = String(formData.get("id") ?? "");
    const items = await getGallery();
    const idx = items.findIndex((g) => g.id === id);
    if (idx < 0) throw new Error("Photo introuvable.");
    const alt = String(formData.get("alt") ?? "").trim();
    const category = String(formData.get("category") ?? "").trim();
    if (!(GALLERY_CATEGORIES as readonly string[]).includes(category)) {
      throw new Error("Catégorie invalide.");
    }
    items[idx] = { ...items[idx], alt, category };
    await saveGallery(items);
    revalidatePublic();
  } catch (error) {
    return { error: publicError(error, "Modification impossible.") };
  }
  redirect(adminPath("/mediatheque?ok=1"));
}

export async function deleteGalleryItemAction(formData: FormData) {
  await guard();
  const id = String(formData.get("id") ?? "");
  const items = await getGallery();
  const item = items.find((g) => g.id === id);
  if (item && isUploadSrc(item.src)) await removeUploadSrc(item.src);
  await saveGallery(items.filter((g) => g.id !== id));
  revalidatePublic();
  redirect(adminPath("/mediatheque"));
}

export async function moveGalleryItemAction(formData: FormData) {
  await guard();
  const id = String(formData.get("id") ?? "");
  const dir = String(formData.get("dir") ?? "");
  const items = await getGallery();
  const idx = items.findIndex((g) => g.id === id);
  if (idx < 0) redirect(adminPath("/mediatheque"));
  const swap = dir === "up" ? idx - 1 : idx + 1;
  if (swap < 0 || swap >= items.length) redirect(adminPath("/mediatheque"));
  const tmp = items[idx];
  items[idx] = items[swap];
  items[swap] = tmp;
  await saveGallery(items);
  revalidatePublic();
  redirect(adminPath("/mediatheque"));
}

export async function saveSchedulesAction(
  _prev: { error?: string } | null,
  formData: FormData,
) {
  await guard();
  try {
    const raw = String(formData.get("payload") ?? "");
    const parsed = JSON.parse(raw) as {
      kids: KidsGroup[];
      adults: AdultGroup[];
    };
    if (!Array.isArray(parsed.kids) || !Array.isArray(parsed.adults)) {
      throw new Error("Données horaires invalides.");
    }
    await saveSchedules(parsed);
    revalidatePublic();
  } catch (error) {
    return { error: publicError(error, "Enregistrement impossible.") };
  }
  redirect(adminPath("/horaires?ok=1"));
}

export async function savePricingAction(
  _prev: { error?: string } | null,
  formData: FormData,
) {
  await guard();
  try {
    const raw = String(formData.get("payload") ?? "");
    const parsed = JSON.parse(raw) as PricingPlan[];
    if (!Array.isArray(parsed)) throw new Error("Données tarifs invalides.");
    await savePricing(
      parsed.map((p) => ({
        ...p,
        id: p.id || newId("price"),
        club: Number(p.club) || 0,
        license:
          p.license === null || p.license === undefined || p.license === ("" as never)
            ? null
            : Number(p.license),
      })),
    );
    revalidatePublic();
  } catch (error) {
    return { error: publicError(error, "Enregistrement impossible.") };
  }
  redirect(adminPath("/tarifs?ok=1"));
}

export async function saveInstructorAction(
  _prev: { error?: string } | null,
  formData: FormData,
) {
  await guard();
  try {
    const id = String(formData.get("id") ?? "").trim() || newId("inst");
    const list = await getInstructors();
    const existing = list.find((i) => i.id === id);
    let image = existing?.image || "";
    const file = formData.get("imageFile");
    if (file instanceof File && file.size > 0) {
      if (image && isUploadSrc(image)) await removeUploadSrc(image);
      image = await saveImageUpload(file, "instructors", id);
    }
    const ranks = String(formData.get("ranks") ?? "")
      .split("\n")
      .map((r) => r.trim())
      .filter(Boolean);
    const person: Instructor = {
      id,
      name: String(formData.get("name") ?? "").trim(),
      image,
      ranks,
      bio: String(formData.get("bio") ?? "").trim(),
    };
    if (!person.name) throw new Error("Le nom est obligatoire.");
    const idx = list.findIndex((i) => i.id === id);
    if (idx >= 0) list[idx] = person;
    else list.push(person);
    await saveInstructors(list);
    revalidatePublic();
  } catch (error) {
    return { error: publicError(error, "Enregistrement impossible.") };
  }
  redirect(adminPath("/instructeurs?ok=1"));
}

export async function deleteInstructorAction(formData: FormData) {
  await guard();
  const id = String(formData.get("id") ?? "");
  const list = await getInstructors();
  const person = list.find((i) => i.id === id);
  if (person && isUploadSrc(person.image)) await removeUploadSrc(person.image);
  await saveInstructors(list.filter((i) => i.id !== id));
  revalidatePublic();
  redirect(adminPath("/instructeurs"));
}

export async function saveClubAction(
  _prev: { error?: string } | null,
  formData: FormData,
) {
  await guard();
  try {
    const current = await getClub();
    const locCount = Number(formData.get("locCount") ?? 0);
    const locations = [];
    for (let i = 0; i < locCount; i += 1) {
      locations.push({
        name: String(formData.get(`loc_name_${i}`) ?? "").trim(),
        address: String(formData.get(`loc_address_${i}`) ?? "").trim(),
        city: String(formData.get(`loc_city_${i}`) ?? "").trim(),
        short: String(formData.get(`loc_short_${i}`) ?? "").trim(),
        mapsUrl: sanitizeHref(String(formData.get(`loc_maps_${i}`) ?? ""), true),
      });
    }
    const next: ClubInfo = {
      ...current,
      name: String(formData.get("name") ?? "").trim() || current.name,
      fullName: String(formData.get("fullName") ?? "").trim() || current.fullName,
      tagline: String(formData.get("tagline") ?? "").trim() || current.tagline,
      email: String(formData.get("email") ?? "").trim() || current.email,
      association:
        String(formData.get("association") ?? "").trim() || current.association,
      rna: String(formData.get("rna") ?? "").trim() || current.rna,
      siege: String(formData.get("siege") ?? "").trim() || current.siege,
      mapImage: String(formData.get("mapImage") ?? "").trim() || current.mapImage,
      mapLink:
        sanitizeHref(String(formData.get("mapLink") ?? ""), true) ||
        current.mapLink,
      locations: locations.filter((l) => l.name),
    };
    await saveClub(next);
    revalidatePublic();
  } catch (error) {
    return { error: publicError(error, "Enregistrement impossible.") };
  }
  redirect(adminPath("/club?ok=1"));
}

export type { GalleryItem };
