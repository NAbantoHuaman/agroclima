import Constants from "expo-constants";
import { NativeModules } from "react-native";
import type {
  RecommendRequestPayload,
  RecommendResponse,
  ReferenceDataResponse,
  VoiceAssistantRequestPayload,
  VoiceAssistantResponse,
  VoiceAudioRequestPayload,
} from "../types";

let customServerUrl: string | null = null;
let cachedActiveApiBase: string | null = null;
let activeProbePromise: Promise<string> | null = null;

export function setCustomApiBaseUrl(url: string | null) {
  customServerUrl = url ? url.replace(/\/+$/, "") : null;
  cachedActiveApiBase = null;
  activeProbePromise = null;
}

export function getCustomApiBaseUrl(): string | null {
  return customServerUrl;
}

export function getActiveApiBaseUrl(): string | null {
  return cachedActiveApiBase;
}

function appendHostCandidates(rawHostUri: string, bases: string[]): void {
  const cleanHost = rawHostUri.replace(/^https?:\/\//i, "").split("/")[0];
  if (!cleanHost) return;
  const ipPart = cleanHost.split(":")[0];
  if (ipPart && /^\d+\.\d+\.\d+\.\d+$/.test(ipPart)) {
    bases.push(`http://${ipPart}:8000/api`);
    bases.push(`http://${cleanHost}/agro-api`);
  } else {
    bases.push(`https://${cleanHost}/agro-api`);
    bases.push(`http://${cleanHost}/agro-api`);
  }
}

const DEFAULT_CLOUD_API_URL = "https://agroclima-fx55.onrender.com/api";

/**
 * Builds candidate backend `/api` (or Metro `/agro-api`) base URLs in priority order:
 * 1. Explicit custom server URL
 * 2. Active LAN FastAPI server / Metro /agro-api during local Expo Go dev
 * 3. Build-time EXPO_PUBLIC_API_URL or default cloud HTTPS backend (Render)
 * 4. Local loopback fallback
 */
export function resolveApiBaseCandidates(): string[] {
  const bases: string[] = [];

  if (customServerUrl) {
    const clean = customServerUrl.replace(/\/+$/, "");
    bases.push(clean.endsWith("/api") || clean.endsWith("/agro-api") ? clean : `${clean}/api`);
  }

  const hostUri =
    Constants.expoConfig?.hostUri ||
    (
      Constants as unknown as {
        manifest2?: { extra?: { expoClient?: { hostUri?: string } } };
      }
    ).manifest2?.extra?.expoClient?.hostUri;

  if (hostUri && typeof hostUri === "string") {
    appendHostCandidates(hostUri, bases);
  }

  try {
    const scriptURL = (
      NativeModules as { SourceCode?: { scriptURL?: string } }
    )?.SourceCode?.scriptURL;
    if (scriptURL && /^https?:\/\//i.test(scriptURL)) {
      const m = scriptURL.match(/^https?:\/\/([^/]+)/i);
      if (m && m[1]) {
        appendHostCandidates(m[1], bases);
      }
    }
  } catch {
    // ignore
  }

  const publicApiUrl = process.env.EXPO_PUBLIC_API_URL;
  if (publicApiUrl && typeof publicApiUrl === "string" && publicApiUrl.trim()) {
    const cleanPub = publicApiUrl.trim().replace(/\/+$/, "");
    bases.push(cleanPub.endsWith("/api") || cleanPub.endsWith("/agro-api") ? cleanPub : `${cleanPub}/api`);
  }

  bases.push(DEFAULT_CLOUD_API_URL);
  bases.push("http://127.0.0.1:8000/api");
  return Array.from(new Set(bases));
}

export function resolveEndpointCandidates(routeSuffix: string): string[] {
  const cleanSuffix = routeSuffix.startsWith("/") ? routeSuffix : `/${routeSuffix}`;
  return resolveApiBaseCandidates().map((b) => `${b}${cleanSuffix}`);
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = 15000
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        "ngrok-skip-browser-warning": "1",
      },
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

class HttpResponseError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function probeBaseGroup(bases: string[], timeoutMs: number): Promise<string | null> {
  if (bases.length === 0) return null;
  const checks = await Promise.allSettled(
    bases.map(async (base) => {
      const res = await fetchWithTimeout(`${base}/health`, {}, timeoutMs);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return base;
    })
  );
  const healthySet = new Set(
    checks
      .filter((c): c is PromiseFulfilledResult<string> => c.status === "fulfilled")
      .map((c) => c.value)
  );
  return bases.find((b) => healthySet.has(b)) ?? null;
}

async function probeHealthyBase(): Promise<string> {
  if (cachedActiveApiBase) {
    try {
      const quickTimeout = cachedActiveApiBase.startsWith("https://") ? 20000 : 2500;
      const quick = await fetchWithTimeout(`${cachedActiveApiBase}/health`, {}, quickTimeout);
      if (quick.ok) return cachedActiveApiBase;
    } catch {
      cachedActiveApiBase = null;
    }
  }

  if (activeProbePromise) {
    return activeProbePromise;
  }

  activeProbePromise = (async () => {
    const candidates = resolveApiBaseCandidates();
    if (customServerUrl && candidates.length > 0) {
      const explicitMatch = await probeBaseGroup(
        [candidates[0]],
        candidates[0].startsWith("https://") ? 45000 : 5000
      );
      if (explicitMatch) {
        cachedActiveApiBase = explicitMatch;
        return explicitMatch;
      }
    }

    const localCandidates = candidates.filter(
      (b) => b.startsWith("http://") && !b.includes("127.0.0.1")
    );
    const localChosen = await probeBaseGroup(localCandidates, 2500);
    if (localChosen) {
      cachedActiveApiBase = localChosen;
      return localChosen;
    }

    const cloudCandidates = candidates.filter((b) => b.startsWith("https://"));
    const cloudChosen = await probeBaseGroup(cloudCandidates, 45000);
    if (cloudChosen) {
      cachedActiveApiBase = cloudChosen;
      return cloudChosen;
    }

    const loopbackCandidates = candidates.filter((b) => b.includes("127.0.0.1"));
    const loopbackChosen = await probeBaseGroup(loopbackCandidates, 2000);
    if (loopbackChosen) {
      cachedActiveApiBase = loopbackChosen;
      return loopbackChosen;
    }

    throw new Error(
      `No se pudo conectar al servidor agronómico (${candidates.slice(0, 2).join(", ")}). ` +
        "Verifica tu conexión a internet o que el backend esté activo."
    );
  })().finally(() => {
    activeProbePromise = null;
  });

  return activeProbePromise;
}

function isAbortError(err: unknown): boolean {
  return (
    err instanceof Error &&
    (err.name === "AbortError" || /\babort(ed)?\b/i.test(err.message))
  );
}

async function callBackendJson<T>(
  routeSuffix: string,
  options: RequestInit,
  timeoutMs: number
): Promise<{ data: T; endpointUsed: string }> {
  const cleanSuffix = routeSuffix.startsWith("/") ? routeSuffix : `/${routeSuffix}`;
  const primaryBase = await probeHealthyBase();
  const candidates = Array.from(
    new Set([primaryBase, ...resolveApiBaseCandidates()])
  );

  let lastErr: unknown = null;
  for (let i = 0; i < candidates.length; i += 1) {
    const base = candidates[i];
    const url = `${base}${cleanSuffix}`;
    if (i > 0) {
      try {
        const pingMs = base.startsWith("https://") ? 20000 : 2000;
        const ping = await fetchWithTimeout(`${base}/health`, {}, pingMs);
        if (!ping.ok) continue;
      } catch {
        continue;
      }
    }

    try {
      const res = await fetchWithTimeout(url, options, timeoutMs);
      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        const detail = errJson?.detail ? String(errJson.detail) : `Error HTTP ${res.status}`;
        if (res.status >= 502 && res.status <= 504 && i < candidates.length - 1) {
          lastErr = new HttpResponseError(res.status, detail);
          cachedActiveApiBase = null;
          continue;
        }
        throw new HttpResponseError(res.status, detail);
      }

      const data = (await res.json()) as T;
      cachedActiveApiBase = base;
      return { data, endpointUsed: url };
    } catch (err) {
      lastErr = err;
      cachedActiveApiBase = null;
      if (
        isAbortError(err) ||
        (err instanceof HttpResponseError && err.status < 502)
      ) {
        break;
      }
    }
  }

  if (isAbortError(lastErr)) {
    throw new Error(
      "El servidor tardó demasiado consultando NASA POWER / Copernicus DEM. Intenta de nuevo."
    );
  }
  if (lastErr instanceof HttpResponseError) {
    throw new Error(lastErr.message);
  }
  throw new Error(
    "Se perdió la conexión con el backend NASA. Verifica red o servidor."
  );
}

export interface ApiExecutionResult<T> {
  data: T;
  sourceMode: "lan_backend";
  endpointUsed: string;
}

export async function requestReferenceData(): Promise<
  ApiExecutionResult<ReferenceDataResponse>
> {
  const { data, endpointUsed } = await callBackendJson<ReferenceDataResponse>(
    "/reference-data",
    { method: "GET" },
    35000
  );
  return { data, sourceMode: "lan_backend", endpointUsed };
}

export interface GeocodePlaceResponse {
  query: string;
  found: boolean;
  result: {
    lat: number;
    lon: number;
    label: string;
    source?: string;
  } | null;
}

export async function requestGeocodePlace(
  query: string
): Promise<ApiExecutionResult<GeocodePlaceResponse>> {
  const encoded = encodeURIComponent(query.trim());
  const { data, endpointUsed } = await callBackendJson<GeocodePlaceResponse>(
    `/geocode?q=${encoded}`,
    { method: "GET" },
    25000
  );
  return { data, sourceMode: "lan_backend", endpointUsed };
}

export async function requestRecommendations(
  payload: RecommendRequestPayload
): Promise<ApiExecutionResult<RecommendResponse>> {
  const { data, endpointUsed } = await callBackendJson<RecommendResponse>(
    "/recommend",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    48000
  );
  return { data, sourceMode: "lan_backend", endpointUsed };
}

export async function requestVoiceAssistant(
  payload: VoiceAssistantRequestPayload
): Promise<ApiExecutionResult<VoiceAssistantResponse>> {
  const { data, endpointUsed } = await callBackendJson<VoiceAssistantResponse>(
    "/voice-assistant",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    38000
  );
  return { data, sourceMode: "lan_backend", endpointUsed };
}

export async function requestVoiceAudio(
  payload: VoiceAudioRequestPayload
): Promise<ApiExecutionResult<VoiceAssistantResponse>> {
  const { data, endpointUsed } = await callBackendJson<VoiceAssistantResponse>(
    "/voice-audio",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    45000
  );
  return { data, sourceMode: "lan_backend", endpointUsed };
}
