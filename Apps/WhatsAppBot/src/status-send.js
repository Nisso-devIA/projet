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

export function bareLid(jid) {
  const raw = String(jid || "");
  if (!raw.endsWith("@lid") && !raw.endsWith("@hosted.lid")) return "";
  const user = raw.split("@")[0].split(":")[0];
  if (!user) return "";
  return `${user}@lid`;
}

export function deviceToJid(device) {
  if (typeof device?.jid === "string" && device.jid) return device.jid;
  const user = String(device?.user || "").replace(/\D/g, "");
  if (!user) return "";
  const server = device?.server === "lid" ? "lid" : "s.whatsapp.net";
  const dev = Number(device?.device) || 0;
  return dev ? `${user}:${dev}@${server}` : `${user}@${server}`;
}

export async function resolveStatusRecipients(jids, { getLids, ownLid } = {}) {
  const lids = new Set();
  const phones = [];
  for (const jid of jids || []) {
    const lid = bareLid(jid);
    if (lid) lids.add(lid);
    else {
      const phone = bareUserJid(jid);
      if (phone) phones.push(phone);
    }
  }
  const uniquePhones = [...new Set(phones)];
  const own = bareLid(ownLid);
  if (own) lids.add(own);
  if (typeof getLids !== "function") {
    return {
      mode: "pn",
      recipients: [...new Set(uniquePhones.concat([...lids]))],
      resolved: 0,
      unresolved: 0,
    };
  }
  let resolved = 0;
  let unresolved = 0;
  for (const chunk of chunkList(uniquePhones, 20)) {
    let rows = null;
    try {
      rows = await getLids(chunk);
    } catch {
      unresolved += chunk.length;
      continue;
    }
    const found = new Map();
    for (const row of rows || []) {
      const phone = bareUserJid(row?.pn);
      const lid = bareLid(row?.lid);
      if (phone && lid) found.set(phone, lid);
    }
    for (const phone of chunk) {
      const lid = found.get(phone);
      if (lid) {
        lids.add(lid);
        resolved += 1;
      } else {
        unresolved += 1;
      }
    }
  }
  if (!lids.size) {
    return { mode: "pn", recipients: uniquePhones, resolved: 0, unresolved };
  }
  return { mode: "lid", recipients: [...lids], resolved, unresolved };
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
    if (waited?.status === 479 || waited?.error === 479) return 479;
    if (waited?.acked) status = waited.status;
  }
  return status;
}

function statusConfirmed(status) {
  if (status === 479 || status === "479" || status === 0 || status === "ERROR") return false;
  if (status === "RECEIPT") return true;
  if (typeof status === "number") return status >= 2;
  return status === "SERVER_ACK" || status === "DELIVERY_ACK" || status === "READ" || status === "PLAYED";
}
