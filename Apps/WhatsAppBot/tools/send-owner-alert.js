import { sendOwnerAlert } from "./owner-alert.js";

const text = process.argv.slice(2).join(" ").trim();
const kind = process.env.ALERT_KIND || "down";

if (!text) {
  console.error("Usage: node tools/send-owner-alert.js <message>");
  process.exit(1);
}

const ok = await sendOwnerAlert(text, { kind, force: process.env.ALERT_FORCE === "1" });
process.exit(ok ? 0 : 1);
