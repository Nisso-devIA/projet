import { unstable_noStore as noStore } from "next/cache";
import { readJsonFile, writeJsonFile } from "@/lib/json-store";
import {
  defaultClub,
  defaultEvents,
  defaultGallery,
  defaultInstructors,
  defaultPricing,
  defaultSchedules,
  type ClubEvent,
  type ClubInfo,
  type GalleryItem,
  type Instructor,
  type PricingPlan,
  type Schedules,
} from "@/content/defaults";

export async function getClub(): Promise<ClubInfo> {
  noStore();
  return readJsonFile("club.json", defaultClub);
}

export async function saveClub(data: ClubInfo) {
  await writeJsonFile("club.json", data);
}

export async function getGallery(): Promise<GalleryItem[]> {
  noStore();
  return readJsonFile("gallery.json", defaultGallery);
}

export async function saveGallery(items: GalleryItem[]) {
  await writeJsonFile("gallery.json", items);
}

export async function getInstructors(): Promise<Instructor[]> {
  noStore();
  return readJsonFile("instructors.json", defaultInstructors);
}

export async function saveInstructors(items: Instructor[]) {
  await writeJsonFile("instructors.json", items);
}

export async function getSchedules(): Promise<Schedules> {
  noStore();
  return readJsonFile("schedules.json", defaultSchedules);
}

export async function saveSchedules(data: Schedules) {
  await writeJsonFile("schedules.json", data);
}

export async function getPricing(): Promise<PricingPlan[]> {
  noStore();
  return readJsonFile("pricing.json", defaultPricing);
}

export async function savePricing(items: PricingPlan[]) {
  await writeJsonFile("pricing.json", items);
}

export async function getEvents(): Promise<ClubEvent[]> {
  noStore();
  return readJsonFile("events.json", defaultEvents);
}

export async function saveEvents(items: ClubEvent[]) {
  await writeJsonFile("events.json", items);
}

export function splitEvents(events: ClubEvent[]) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const upcoming: ClubEvent[] = [];
  const past: ClubEvent[] = [];
  for (const event of events) {
    const d = new Date(`${event.date}T12:00:00`);
    if (Number.isNaN(d.getTime()) || d < today) past.push(event);
    else upcoming.push(event);
  }
  upcoming.sort((a, b) => a.date.localeCompare(b.date));
  past.sort((a, b) => b.date.localeCompare(a.date));
  return { upcoming, past };
}

export function formatEventDate(isoDate: string) {
  const d = new Date(`${isoDate}T12:00:00`);
  if (Number.isNaN(d.getTime())) return isoDate;
  return new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(d);
}
