/** Attributs communs pour ne pas fuiter le MDP (clavier, autofill, historique). */
export const passwordInputProps = {
  type: "password" as const,
  spellCheck: false as const,
  autoCapitalize: "none" as const,
  autoComplete: "current-password" as const,
};

export const newPasswordInputProps = {
  ...passwordInputProps,
  autoComplete: "new-password" as const,
};

export async function postPasswordJson(
  url: string,
  body: Record<string, unknown>,
) {
  return fetch(url, {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(body),
  });
}
