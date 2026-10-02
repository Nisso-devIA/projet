import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

export async function readJsonFile<T>(fileName: string, fallback: T): Promise<T> {
  const file = path.join(process.cwd(), "data", fileName);
  try {
    const raw = await readFile(file, "utf8");
    return JSON.parse(raw) as T;
  } catch {
    await mkdir(path.dirname(file), { recursive: true });
    await writeFile(file, `${JSON.stringify(fallback, null, 2)}\n`, "utf8");
    return structuredClone(fallback);
  }
}

export async function writeJsonFile<T>(fileName: string, data: T) {
  const file = path.join(process.cwd(), "data", fileName);
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, `${JSON.stringify(data, null, 2)}\n`, "utf8");
}
