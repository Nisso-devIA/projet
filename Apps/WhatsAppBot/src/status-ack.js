/** Accusé serveur d'une story. 1 = PENDING, pas encore confirmé. */

const NAMED_ACK = new Set(["SERVER_ACK", "DELIVERY_ACK", "READ", "PLAYED"]);

export function isServerAck(status) {
  if (status === 479 || status === "479" || status === 0 || status === "ERROR") return false;
  if (status === "RECEIPT") return true;
  if (typeof status === "number") return status >= 2;
  return NAMED_ACK.has(status);
}

export function watchStatusDelivery(emitter, messageId, timeoutMs = 20_000) {
  return new Promise((resolve) => {
    if (!emitter || !messageId) {
      resolve({ acked: false, status: null, receipts: 0 });
      return;
    }
    let settled = false;
    let receipts = 0;
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (typeof emitter.off === "function") {
        emitter.off("messages.update", onUpdate);
        emitter.off("message-receipt.update", onReceipt);
      }
      resolve(result);
    };
    const onUpdate = (updates) => {
      for (const item of updates || []) {
        if (item?.key?.id !== messageId) continue;
        const params = item?.update?.messageStubParameters || [];
        const code = params.length ? String(params[0]) : "";
        if (code === "479" || item?.update?.status === 479) {
          finish({ acked: false, status: 479, error: 479, receipts });
          return;
        }
        const status = item?.update?.status;
        if (isServerAck(status)) finish({ acked: true, status, receipts });
      }
    };
    const onReceipt = (updates) => {
      for (const item of updates || []) {
        if (item?.key?.id !== messageId) continue;
        if (item?.receipt?.receiptTimestamp || item?.receipt?.readTimestamp) {
          receipts += 1;
          finish({ acked: true, status: "RECEIPT", receipts });
        }
      }
    };
    const timer = setTimeout(() => finish({ acked: false, status: null, receipts }), timeoutMs);
    emitter.on("messages.update", onUpdate);
    emitter.on("message-receipt.update", onReceipt);
  });
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
    schedule(kind, title, messageId) {
      if (!pending) {
        pending = { kind, title, messageId, used: false, exhausted: false };
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
      const job = { kind: pending.kind, title: pending.title };
      if (pending.messageId) job.messageId = pending.messageId;
      return job;
    },
    clear() {
      pending = null;
    },
  };
}
