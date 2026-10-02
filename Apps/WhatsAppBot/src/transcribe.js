import { execFile } from "node:child_process";
import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { promisify } from "node:util";
import ffmpegPath from "ffmpeg-static";
import wavefile from "wavefile";
import { config, ROOT_DIR } from "./config.js";

const { WaveFile } = wavefile;

const execFileAsync = promisify(execFile);
const TMP_DIR = join(ROOT_DIR, "tmp");

let localPipeline = null;
let localPipelineLoading = null;

function formatDuration(seconds) {
  const total = Number(seconds) || 0;
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

async function transcribeViaApi(buffer, filename, mimetype) {
  const groq = config.groqKey;
  const openai = config.openaiKey;
  if (!groq && !openai) return null;

  const url = groq
    ? "https://api.groq.com/openai/v1/audio/transcriptions"
    : "https://api.openai.com/v1/audio/transcriptions";
  const key = groq || openai;
  const model = groq ? "whisper-large-v3" : "whisper-1";

  const form = new FormData();
  form.append("file", new Blob([buffer], { type: mimetype || "audio/ogg" }), filename);
  form.append("model", model);
  form.append("language", config.transcribeLanguage || "fr");
  form.append("response_format", "json");

  const res = await fetch(url, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}` },
    body: form,
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API transcription ${res.status}: ${body.slice(0, 200)}`);
  }

  const data = await res.json();
  return String(data.text || "").trim();
}

async function getLocalPipeline() {
  if (localPipeline) return localPipeline;
  if (localPipelineLoading) return localPipelineLoading;

  localPipelineLoading = (async () => {
    console.log("Chargement du modèle Whisper local (une seule fois)…");
    const { pipeline } = await import("@xenova/transformers");
    localPipeline = await pipeline("automatic-speech-recognition", "Xenova/whisper-base");
    console.log("Modèle Whisper prêt.");
    return localPipeline;
  })();

  try {
    return await localPipelineLoading;
  } finally {
    localPipelineLoading = null;
  }
}

export function warmupWhisper() {
  if (config.groqKey || config.openaiKey) return Promise.resolve();
  return getLocalPipeline().catch((err) => {
    console.error("Warmup Whisper :", err.message);
  });
}

function wavToFloat32(wavBuffer) {
  const wav = new WaveFile(new Uint8Array(wavBuffer));
  wav.toBitDepth("32f");
  wav.toSampleRate(16000);
  let audioData = wav.getSamples();
  if (Array.isArray(audioData)) {
    if (audioData.length > 1) {
      const merged = new Float32Array(audioData[0].length);
      for (let i = 0; i < audioData[0].length; i += 1) {
        merged[i] = (audioData[0][i] + audioData[1][i]) / 2;
      }
      audioData = merged;
    } else {
      audioData = audioData[0];
    }
  }
  return audioData;
}

async function transcribeLocal(oggPath) {
  const wavPath = oggPath.replace(/\.[^.]+$/, ".wav");
  if (!ffmpegPath) {
    throw new Error("ffmpeg-static introuvable");
  }

  await execFileAsync(ffmpegPath, [
    "-y",
    "-i",
    oggPath,
    "-ar",
    "16000",
    "-ac",
    "1",
    "-f",
    "wav",
    wavPath,
  ]);

  try {
    const wavBuffer = await readFile(wavPath);
    const audioData = wavToFloat32(wavBuffer);
    const asr = await getLocalPipeline();
    const result = await asr(audioData, {
      language: "french",
      task: "transcribe",
    });
    return String(result?.text || "").trim();
  } finally {
    await unlink(wavPath).catch(() => {});
  }
}

export async function transcribeAudioBuffer(buffer, mimetype = "audio/ogg") {
  const apiText = await transcribeViaApi(buffer, "vocal.ogg", mimetype).catch((err) => {
    console.error("Transcription API :", err.message);
    return null;
  });
  if (apiText) return apiText;

  await mkdir(TMP_DIR, { recursive: true });
  const oggPath = join(TMP_DIR, `vocal-${Date.now()}-${Math.random().toString(16).slice(2)}.ogg`);
  await writeFile(oggPath, buffer);
  try {
    return await transcribeLocal(oggPath);
  } finally {
    await unlink(oggPath).catch(() => {});
  }
}

export function formatTranscript({ pushName, seconds, text }) {
  const who = pushName || "Contact";
  const duration = formatDuration(seconds);
  const body = text || "(aucun texte reconnu)";
  return `🎙️ *Transcription* · ${who} · ${duration}\n${body}`;
}
