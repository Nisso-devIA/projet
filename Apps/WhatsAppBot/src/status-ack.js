/** Accusé serveur d'une story. 1 = PENDING, pas encore confirmé. */

const NAMED_ACK = new Set(["SERVER_ACK", "DELIVERY_ACK", "READ", "PLAYED"]);

export function isServerAck(status) {
  if (typeof status === "number") return status >= 2;
  return NAMED_ACK.has(status);
}

export function watchServerAck(emitter, messageId, timeoutMs = 20_000) {
  return new Promise((resolve) => {
    if (!emitter || !messageId) {
      resolve({ acked: false, status: null });
      return;
    }
    let settled = false;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (typeof emitter.off === "function") emitter.off("messages.update", onUpdate);
      resolve(result);
    };
    const onUpdate = (updates) => {
      for (const item of updates || []) {
        if (item?.key?.id !== messageId) continue;
        const status = item?.update?.status;
        if (isServerAck(status)) finish({ acked: true, status });
      }
    };
    const timer = setTimeout(() => finish({ acked: false, status: null }), timeoutMs);
    emitter.on("messages.update", onUpdate);
  });
}

export function createStatusRetry() {
  let pending = null;
  return {
    schedule(kind, title) {
      if (!pending) {
        pending = { kind, title, used: false, exhausted: false };
        return "scheduled";
      }
      if (pending.used && !pending.exhausted) {
        pending.exhausted = true;
        return "exhausted";
      }
      return pending.exhausted ? "exhausted" : "already";
    },
    take() {
      if (!pending || pending.used || pending.exhausted) return null;
      pending = { ...pending, used: true };
      return { kind: pending.kind, title: pending.title };
    },
    clear() {
      pending = null;
    },
  };
}
