const TOKEN_KEY = "astrolive:token";
const UID_KEY = "astrolive:uid";

try {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(UID_KEY);
} catch {
  /* private mode */
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const GENERIC = "Something went wrong on our end. Try again.";
const OTP_CODES = new Set([
  "EMAIL_SEND_FAILED",
  "RATE_LIMITED",
  "CODE_EXPIRED",
  "CODE_INVALID",
  "TOO_MANY_ATTEMPTS",
  "INVALID_EMAIL",
]);

export const isAuthError = (err: unknown) =>
  err instanceof ApiError && err.code === "AUTH_REQUIRED";

type ErrorBody = {
  error?: { code?: string; userMessage?: string; message?: string; devDetail?: string };
  userMessage?: string;
};

const readError = async (r: Response): Promise<ApiError> => {
  let code = r.status === 401 ? "AUTH_REQUIRED" : "ERROR";
  try {
    const body = (await r.json()) as ErrorBody;
    if (body.error?.code) code = body.error.code;
    const user = body.error?.userMessage || body.userMessage;
    if (typeof user === "string" && user.trim()) {
      return new ApiError(user.trim(), r.status, code);
    }
  } catch {
    /* ignore non-JSON */
  }
  return new ApiError(GENERIC, r.status, code);
};

let authLost: (() => void) | null = null;

export const onUnauthorized = (fn: (() => void) | null) => {
  authLost = fn;
};

export const getToken = () => null;
export const getUid = () => null;
export const setSession = (_token: string, _uid: string) => undefined;
export const clearSession = () => {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(UID_KEY);
  } catch {
    /* ignore */
  }
};

const json = async (res: Promise<Response>) => {
  const r = await res;
  if (!r.ok) {
    const err = await readError(r);
    if (err.status === 401 && !OTP_CODES.has(err.code) && err.code === "AUTH_REQUIRED") {
      clearSession();
      authLost?.();
    }
    throw err;
  }
  return r.json();
};

const headers = (): HeadersInit => ({ "Content-Type": "application/json" });

const API_BASE = String(import.meta.env.VITE_API_URL ?? "")
  .trim()
  .replace(/\/$/, "")
  .replace(/\/api$/, "");

const req = (path: string, init: RequestInit = {}) =>
  fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: { ...headers(), ...(init.headers || {}) },
  });

export type City = { name: string; lat: number; lon: number };

export type ChartPos = {
  graha: string;
  lon: number;
  dms: string;
  rashi: string;
  rashi_en: string;
  house: number;
  nakshatra: string;
  pada: number;
};

export type Chart = {
  lagna: string;
  lagna_en: string;
  chandra_rashi: string;
  nakshatra: string;
  pada: number;
  ayanamsha: number;
  mangal: { status: string; from_lagna: boolean; from_moon: boolean };
  positions: ChartPos[];
};

export type Panchang = {
  now: string;
  date: string;
  tithi: string;
  nakshatra: string;
  pada: number;
  sunrise: string;
  sunset: string;
  abhijit: { start: string; end: string; active: boolean };
  rahu_kaal: { start: string; end: string; active: boolean };
  lagna: string;
  upay: string;
  note: string;
  streak: number;
  upay_done: boolean;
  wallet: number;
  user: { name: string; lagna: string; nakshatra: string };
};

export type Koot = { name: string; max: number; score: number; ok: boolean };

export type MatchResult = {
  gunas: number;
  max: number;
  verdict: string;
  mangal: string;
  delta_dosha: number;
  koots: Koot[];
  nadi: { score: number; max: number };
  bhakoot: { score: number; max: number };
  a: { name: string; nakshatra: string; rashi: string };
  b: { name: string; nakshatra: string; rashi: string };
};

export type Astrologer = {
  id: string;
  initials: string;
  name: string;
  speciality: string;
  years: number;
  rating: number;
  rate: number;
  available: boolean;
  languages: string[];
};

export type SamadhanItem = {
  id: string;
  kind: string;
  title: string;
  place: string;
  price: number;
  perks: string[];
  cta: string;
};

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type ChatPayload = {
  astrologer: Astrologer;
  messages: ChatMessage[];
  reply?: string;
  fresh?: boolean;
};

export type SessionUser = {
  id: string;
  name: string;
  email?: string;
  place: string;
  wallet: number;
  streak: number;
  lagna?: string;
  nakshatra?: string;
  totp_enabled?: boolean;
};

export type Session = {
  user: SessionUser;
};

export const api = {
  cities: () => json(req("/api/cities")) as Promise<City[]>,
  sendOtp: (email: string) =>
    json(req("/api/auth/otp/send", { method: "POST", body: JSON.stringify({ email }) })) as Promise<{
      ok: boolean;
      sent: boolean;
      retry_after: number;
      expires_in: number;
    }>,
  verifyOtp: (email: string, code: string) =>
    json(req("/api/auth/otp/verify", { method: "POST", body: JSON.stringify({ email, code }) })) as Promise<{
      needs_profile: boolean;
      needs_totp?: boolean;
      ticket?: string;
      email?: string;
      user?: SessionUser;
    }>,
  verifyTotp: (code: string) =>
    json(req("/api/auth/totp/verify", { method: "POST", body: JSON.stringify({ code }) })) as Promise<Session>,
  totpStatus: () => json(req("/api/auth/totp/status")) as Promise<{ enabled: boolean }>,
  totpSetup: () => json(req("/api/auth/totp/setup", { method: "POST" })) as Promise<{ uri: string; secret: string; qr: string }>,
  totpEnable: (code: string) =>
    json(req("/api/auth/totp/enable", { method: "POST", body: JSON.stringify({ code }) })) as Promise<{
      ok: boolean;
      recovery_codes: string[];
      enabled: boolean;
    }>,
  totpDisable: (code: string) =>
    json(req("/api/auth/totp/disable", { method: "POST", body: JSON.stringify({ code }) })) as Promise<{
      ok: boolean;
      enabled: boolean;
    }>,
  register: (body: Record<string, unknown>) =>
    json(req("/api/auth/register", { method: "POST", body: JSON.stringify(body) })) as Promise<Session>,
  login: (body: { email: string; password: string }) =>
    json(req("/api/auth/login", { method: "POST", body: JSON.stringify(body) })) as Promise<Session>,
  logout: () =>
    json(req("/api/auth/logout", { method: "POST" })).finally(() => {
      clearSession();
    }),
  panchang: () => json(req("/api/panchang")) as Promise<Panchang>,
  completeUpay: () => json(req("/api/upay/complete", { method: "POST" })),
  kundali: () =>
    json(req("/api/kundali")) as Promise<{
      chart: Chart;
      name: string;
      place: string;
      dob: string;
      tob: string;
    }>,
  astrologers: () => json(req("/api/astrologers")) as Promise<Astrologer[]>,
  drishti: () => json(req("/api/drishti")),
  samadhan: () => json(req("/api/samadhan")) as Promise<SamadhanItem[]>,
  book: (item_id: string) => json(req("/api/samadhan/book", { method: "POST", body: JSON.stringify({ item_id }) })),
  bookings: () => json(req("/api/bookings")),
  me: () => json(req("/api/me")) as Promise<SessionUser>,
  createLink: (mode: string) =>
    json(req("/api/melapak/link", { method: "POST", body: JSON.stringify({ mode }) })) as Promise<{
      token: string;
      path: string;
      mode: string;
      host: string;
    }>,
  getMatch: (token: string) => json(req(`/api/melapak/${encodeURIComponent(token)}`)),
  joinMatch: (token: string, body: Record<string, unknown>) =>
    json(req(`/api/melapak/${encodeURIComponent(token)}/join`, { method: "POST", body: JSON.stringify(body) })) as Promise<{
      guest_id: string;
      result: MatchResult;
      user?: SessionUser;
    }>,
  demoPriya: () => json(req("/api/melapak/demo/priya")) as Promise<MatchResult>,
  chatHistory: (astrologer_id: string) =>
    json(req(`/api/chat?astrologer_id=${encodeURIComponent(astrologer_id)}`)) as Promise<ChatPayload>,
  chatStart: (astrologer_id: string) =>
    json(req("/api/chat/start", { method: "POST", body: JSON.stringify({ astrologer_id }) })) as Promise<ChatPayload>,
  chatSend: (astrologer_id: string, message: string) =>
    json(
      req("/api/chat", { method: "POST", body: JSON.stringify({ astrologer_id, message }) })
    ) as Promise<ChatPayload>,
};

export { TOKEN_KEY, UID_KEY };
