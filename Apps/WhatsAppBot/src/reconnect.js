/** Délais de reconnexion. 440 = une autre session a pris la place. */

export const REPLACED_CODE = 440;

const DEFAULTS = {
  baseMs: 5_000,
  maxMs: 5 * 60_000,
  replacedBaseMs: 60_000,
  replacedLimit: 3,
};

export function nextDelayMs(status, attempt, options = {}) {
  const opts = { ...DEFAULTS, ...options };
  const step = Math.max(1, Number(attempt) || 1);
  const base = status === REPLACED_CODE ? opts.replacedBaseMs : opts.baseMs;
  const delay = base * 2 ** (step - 1);
  return Math.min(opts.maxMs, delay);
}

export function shouldStopReplaced(streak, options = {}) {
  const limit = options.replacedLimit ?? DEFAULTS.replacedLimit;
  return Number(streak) >= limit;
}
