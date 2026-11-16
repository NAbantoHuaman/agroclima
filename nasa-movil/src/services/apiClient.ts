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

/**
 * Builds candidate backend `/api` (or Metro `/agro-api`) base URLs in priority order:
 * 1. Explicit custom server URL
 * 2. Direct LAN FastAPI server on port 8000 (derived from Expo host / scriptURL IP)
 * 3. Active Metro dev server origin + /agro-api (works through --tunnel ngrok AND --lan)
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

async function probeHealthyBase(): Promise<string> {
  if (cachedActiveApiBase) {
    try {
      const quick = await fetchWithTimeout(`${cachedActiveApiBase}/health`, {}, 2500);
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
    const checks = await Promise.allSettled(
      candidates.map(async (base) => {
        const res = await fetchWithTimeout(`${base}/health`, {}, 3500);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return base;
      })
    );

    const healthySet = new Set(
      checks
        .filter((c): c is PromiseFulfilledResult<string> => c.status === "fulfilled")
        .map((c) => c.value)
    );

    const chosen = candidates.find((b) => healthySet.has(b));
    if (chosen) {
      cachedActiveApiBase = chosen;
      return chosen;
    }

    throw new Error(
      `No se pudo conectar al servidor agronómico NASA (${candidates.slice(0, 3).join(", ")}). ` +
        "Verifica que el backend FastAPI esté encendido en el puerto 8000 o que tu celular esté en la misma red / túnel."
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
        const ping = await fetchWithTimeout(`${base}/health`, {}, 2000);
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
    10000
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
    10000
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
