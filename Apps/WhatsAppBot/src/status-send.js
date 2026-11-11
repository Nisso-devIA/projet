/** Prépare une story pour tous les téléphones, puis réessaie le même id si besoin. */

export const DEVICE_FETCH_CHUNK = 15;
export const SESSION_FETCH_CHUNK = 50;

export function bareUserJid(jid) {
  const raw = String(jid || "");
  if (!raw || raw === "status@broadcast") return "";
  if (raw.endsWith("@g.us") || raw.endsWith("@lid") || raw.endsWith("@broadcast")) return "";
  const user = raw.split("@")[0].split(":")[0].replace(/\D/g, "");
  if (!user) return "";
  return `${user}@s.whatsapp.net`;
}

export function statusRecipients(jids, ownJid) {
  const set = new Set();
  for (const jid of jids || []) {
    const bare = bareUserJid(jid);
    if (bare) set.add(bare);
  }
  const own = bareUserJid(ownJid);
  if (own) set.add(own);
  return [...set];
}

export function chunkList(items, size) {
  const step = Math.max(1, Number(size) || 1);
  const chunks = [];
  for (let index = 0; index < items.length; index += step) {
    chunks.push(items.slice(index, index + step));
  }
  return chunks;
}

export function deviceToJid(device) {
  const user = String(device?.user || "").replace(/\D/g, "");
  if (!user) return "";
  const dev = Number(device?.device) || 0;
  return dev ? `${user}:${dev}@s.whatsapp.net` : `${user}@s.whatsapp.net`;
}

export async function refreshStatusDevices(getUSyncDevices, recipients, chunkSize = DEVICE_FETCH_CHUNK) {
  const chunks = chunkList(recipients, chunkSize);
  if (typeof getUSyncDevices !== "function") {
    return { chunks: chunks.length, devices: 0, failedChunks: 0, deviceJids: [] };
  }
  let devices = 0;
  let failedChunks = 0;
  const deviceJids = [];
  for (const chunk of chunks) {
    try {
      const found = await getUSyncDevices(chunk, false, false);
      for (const item of found || []) {
        const jid = deviceToJid(item);
        if (jid) deviceJids.push(jid);
      }
      devices += Array.isArray(found) ? found.length : 0;
    } catch {
      failedChunks += 1;
    }
  }
  return { chunks: chunks.length, devices, failedChunks, deviceJids };
}

export async function ensureStatusSessions(assertSessions, deviceJids, chunkSize = SESSION_FETCH_CHUNK) {
  if (typeof assertSessions !== "function") return { chunks: 0, failedChunks: 0 };
  const chunks = chunkList(deviceJids, chunkSize);
  let failedChunks = 0;
  for (const chunk of chunks) {
    try {
      await assertSessions(chunk, false);
    } catch {
      failedChunks += 1;
    }
  }
  return { chunks: chunks.length, failedChunks };
}

export async function deliverStatus({ createId, send, waitAck, refresh, maxAttempts = 2 }) {
  const id = createId();
  const prepared = await refresh();
  let status = await finishAttempt(send, waitAck, id);
  let attempts = 1;
  if (!statusConfirmed(status) && maxAttempts > 1) {
    attempts = 2;
    await refresh();
    status = await finishAttempt(send, waitAck, id);
  }
  return {
    id,
    acked: statusConfirmed(status),
    status,
    attempts,
    ...prepared,
  };
}

async function finishAttempt(send, waitAck, id) {
  const sent = await send(id);
  let status = sent?.status ?? null;
  if (!statusConfirmed(status)) {
    const waited = await waitAck(id);
    if (waited?.acked) status = waited.status;
  }
  return status;
}

function statusConfirmed(status) {
  if (typeof status === "number") return status >= 2;
  return status === "SERVER_ACK" || status === "DELIVERY_ACK" || status === "READ" || status === "PLAYED";
}
