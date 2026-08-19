import { useEffect, useRef, useState, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Sunrise,
  LayoutGrid,
  Users,
  Flame,
  Share2,
  Heart,
  ChevronLeft,
  Clock,
  AlertTriangle,
  Sun,
  Moon,
  Compass,
  Gem,
  Check,
  Play,
  MessageSquare,
  Send,
  X,
  Loader2,
  LogOut,
  MoreVertical,
  Shield,
  Mail,
  Maximize2,
  Minimize2,
} from "lucide-react";
import "./al.css";
import {
  api,
  clearSession,
  isAuthError,
  onUnauthorized,
  type Chart as NatalChart,
  type ChartPos,
  type ChatMessage,
  type City,
  type MatchResult,
  type Panchang,
  type SamadhanItem,
  type SessionUser,
} from "./api";

/** Gold line-art portrait of Acharya Kaushik — the in-app baba. */
function Baba({ size = 64 }: { size?: number }) {
  return (
    <svg className="al-baba" width={size} height={size} viewBox="0 0 80 80" aria-hidden="true">
      <defs>
        <radialGradient id={`babaGlow-${size}`} cx="50%" cy="38%" r="62%">
          <stop offset="0%" stopColor="#3A2352" />
          <stop offset="100%" stopColor="#150E22" />
        </radialGradient>
      </defs>
      <circle cx="40" cy="40" r="40" fill={`url(#babaGlow-${size})`} />
      <circle cx="40" cy="40" r="38" fill="none" stroke="#E9CE8E" strokeOpacity=".28" />
      <path d="M18 62c4-14 12-22 22-22s18 8 22 22" fill="#2A183C" />
      <path d="M22 58c6 10 30 10 36 0" fill="none" stroke="#C79A45" strokeWidth="1.2" />
      <ellipse cx="40" cy="36" rx="15" ry="17" fill="#E8C9A0" />
      <path d="M26 34c2-14 26-14 28 0" fill="#1A1024" />
      <path d="M24 36c8-16 24-16 32 0" fill="none" stroke="#E9CE8E" strokeWidth="1.4" />
      <path d="M28 58c3 10 21 10 24 0" fill="#F4E4C8" />
      <path d="M30 56c4 8 16 8 20 0" fill="none" stroke="#C79A45" strokeWidth=".8" />
      <ellipse cx="34" cy="37" rx="2.1" ry="2.4" fill="#1A1024" />
      <ellipse cx="46" cy="37" rx="2.1" ry="2.4" fill="#1A1024" />
      <circle cx="34.6" cy="36.4" r=".6" fill="#F4EFF8" />
      <circle cx="46.6" cy="36.4" r=".6" fill="#F4EFF8" />
      <path d="M32 43.5c5 4 11 4 16 0" fill="none" stroke="#8B4A3A" strokeWidth="1.1" strokeLinecap="round" />
      <path d="M40 28v7" stroke="#C45C3E" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M37.2 30.2h5.6" stroke="#C45C3E" strokeWidth="1.3" strokeLinecap="round" />
      <path d="M18 64c8 8 36 8 44 0" fill="#C79A45" fillOpacity=".35" />
    </svg>
  );
}

const SKY: Array<[number, number]> = [
  [22, 34], [63, 18], [96, 62], [148, 29], [188, 71], [231, 24], [274, 55],
  [312, 38], [345, 78], [44, 96], [124, 108], [206, 118], [292, 96], [52, 152],
  [166, 160], [252, 146], [336, 132], [88, 186], [214, 196], [304, 176],
];
const LINES = [
  [0, 1, 3, 5], [2, 4, 6, 7], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19],
];
const HOUSES = [
  { n: 1, x: 150, y: 74 }, { n: 2, x: 76, y: 33 },
  { n: 3, x: 33, y: 76 }, { n: 4, x: 74, y: 150 },
  { n: 5, x: 33, y: 224 }, { n: 6, x: 76, y: 267 },
  { n: 7, x: 150, y: 226 }, { n: 8, x: 224, y: 267 },
  { n: 9, x: 267, y: 224 }, { n: 10, x: 226, y: 150 },
  { n: 11, x: 267, y: 76 }, { n: 12, x: 224, y: 33 },
];
const GRAHA_ABBR: Record<string, string> = {
  Sun: "Su", Moon: "Ch", Mars: "Ma", Mercury: "Bu", Jupiter: "Gu",
  Venus: "Sk", Saturn: "Sa", Rahu: "Ra", Ketu: "Ke",
};
const RASHIS = ["Mesh", "Vrishabh", "Mithun", "Karka", "Simha", "Kanya", "Tula", "Vrischik", "Dhanu", "Makar", "Kumbh", "Meen"];
const RASHI_DEVA: Record<string, string> = {
  Mesh: "मेष", Vrishabh: "वृषभ", Mithun: "मिथुन", Karka: "कर्क",
  Simha: "सिंह", Kanya: "कन्या", Tula: "तुला", Vrischik: "वृश्चिक",
  Dhanu: "धनु", Makar: "मकर", Kumbh: "कुम्भ", Meen: "मीन",
};
const KOOT_NOTE: Record<string, string> = {
  Varna: "Spiritual compatibility",
  Vashya: "Mutual influence",
  Tara: "Birth-star fortune",
  Yoni: "Temperament match",
  "Graha Maitri": "Mental affinity",
  Gana: "Nature and conduct",
  Bhakoot: "Household harmony",
  Nadi: "Health and progeny",
};
const MODE_KEYS = [
  { k: "bandhan", label: "Bandhan" },
  { k: "saha", label: "Saha-Karya" },
  { k: "mitra", label: "Mitra" },
  { k: "kula", label: "Kula" },
] as const;
const TABS = [
  { k: "today", icon: Sunrise, label: "Aaj" },
  { k: "chart", icon: LayoutGrid, label: "Kundali" },
  { k: "melapak", icon: Users, label: "Melapak" },
  { k: "samadhan", icon: Flame, label: "Samadhan" },
] as const;
type Tab = (typeof TABS)[number]["k"];
const TAB_PATH: Record<Tab, string> = {
  today: "/",
  chart: "/kundali",
  melapak: "/melapak",
  samadhan: "/samadhan",
};
const pathToTab = (pathname: string): Tab => {
  if (pathname.startsWith("/kundali")) return "chart";
  if (pathname.startsWith("/samadhan")) return "samadhan";
  if (pathname === "/melapak") return "melapak";
  return "today";
};

function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

const toMins = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};
const clock = (m: number) => {
  const h = Math.floor(m / 60);
  const mm = Math.floor(m % 60);
  const ap = h >= 12 ? "PM" : "AM";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${hh}:${String(mm).padStart(2, "0")} ${ap}`;
};
const countdown = (m: number) => {
  const t = Math.max(0, m);
  const h = Math.floor(t / 60);
  const mm = Math.floor(t % 60);
  const s = Math.floor((t * 60) % 60);
  return h > 0 ? `${h}h ${mm}m` : `${mm}m ${String(s).padStart(2, "0")}s`;
};
const firstName = (name: string) => name.trim().split(/\s+/)[0] || name;
const fmtDob = (dob: string) => {
  const d = new Date(`${dob}T00:00:00`);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }).toUpperCase();
};

function Sky() {
  return (
    <svg className="al-sky" viewBox="0 0 372 250" fill="none" aria-hidden="true">
      {LINES.map((path, i) => (
        <polyline
          key={i}
          points={path.map((p) => SKY[p].join(",")).join(" ")}
          stroke="#E9CE8E"
          strokeOpacity=".16"
          strokeWidth="1"
          fill="none"
        />
      ))}
      {SKY.map(([x, y], i) => (
        <circle
          key={`${x}-${y}`}
          cx={x}
          cy={y}
          r={i % 4 === 0 ? 1.9 : 1.1}
          fill={i % 3 === 0 ? "#E9CE8E" : "#F4EFF8"}
          className="al-twinkle"
          style={{ animationDelay: `${(i % 7) * 0.55}s` }}
        />
      ))}
    </svg>
  );
}

function Kundali({ chart }: { chart: NatalChart }) {
  const lagnaIdx = Math.max(0, RASHIS.indexOf(chart.lagna));
  const byHouse: Record<number, string[]> = {};
  for (const p of chart.positions) {
    const abbr = GRAHA_ABBR[p.graha] ?? p.graha.slice(0, 2);
    (byHouse[p.house] ??= []).push(abbr);
  }
  const G = "#E9CE8E";
  return (
    <div style={{ position: "relative", padding: "6px 0" }}>
      <div
        className="al-pulse"
        style={{
          position: "absolute",
          inset: "12%",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(233,206,142,.20), transparent 68%)",
          filter: "blur(22px)",
          pointerEvents: "none",
        }}
      />
      <svg viewBox="-16 -16 332 332" style={{ width: "100%", display: "block", position: "relative" }}>
        <circle cx="150" cy="150" r="158" fill="none" stroke={G} strokeOpacity=".1" strokeDasharray="2 9" className="al-spin" />
        <g
          stroke={G}
          strokeOpacity=".55"
          strokeWidth="1.15"
          fill="none"
          style={{ filter: "drop-shadow(0 0 5px rgba(233,206,142,.45))" }}
        >
          <rect x="0" y="0" width="300" height="300" rx="3" />
          <path d="M0 0 L300 300 M300 0 L0 300" />
          <path d="M150 0 L300 150 L150 300 L0 150 Z" />
        </g>
        {HOUSES.map((h) => {
          const gr = byHouse[h.n] || [];
          const rashiNum = ((lagnaIdx + h.n - 1) % 12) + 1;
          return (
            <g key={h.n}>
              <text
                x={h.x}
                y={h.y - (gr.length ? 9 : 0)}
                textAnchor="middle"
                fill={G}
                fillOpacity=".42"
                fontSize="11"
                fontFamily="Poppins, sans-serif"
              >
                {rashiNum}
              </text>
              {gr.map((p, i) => (
                <text
                  key={p}
                  x={h.x}
                  y={h.y + 8 + i * 13}
                  textAnchor="middle"
                  fill="#F4EFF8"
                  fontSize="11.5"
                  fontWeight="500"
                  fontFamily="Poppins, sans-serif"
                >
                  {p}
                </text>
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function ScoreRing({ score, max }: { score: number; max: number }) {
  const r = 62;
  const C = 2 * Math.PI * r;
  const pct = score / max;
  return (
    <div style={{ position: "relative", width: 168, height: 168, margin: "0 auto" }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(233,206,142,.26), transparent 66%)",
          filter: "blur(20px)",
        }}
      />
      <svg viewBox="0 0 168 168" style={{ position: "relative", width: "100%" }}>
        <circle cx="84" cy="84" r={r} fill="none" stroke="#fff" strokeOpacity=".08" strokeWidth="6" />
        <circle
          cx="84"
          cy="84"
          r={r}
          fill="none"
          stroke="#E9CE8E"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${C * pct} ${C}`}
          transform="rotate(-90 84 84)"
          style={{ filter: "drop-shadow(0 0 8px rgba(233,206,142,.6))" }}
        />
        <circle cx="84" cy="84" r={r + 15} fill="none" stroke="#E9CE8E" strokeOpacity=".14" strokeDasharray="1.5 8" className="al-spin" />
        <text x="84" y="86" textAnchor="middle" fill="#F4EFF8" fontSize="46" fontFamily="'Cormorant Garamond', serif" fontWeight="600">
          {score}
        </text>
        <text x="84" y="106" textAnchor="middle" fill="#B0A3C6" fontSize="9.5" letterSpacing="2.4" fontFamily="Poppins, sans-serif">
          OF {max} GUNAS
        </text>
      </svg>
    </div>
  );
}

function Meter({
  icon,
  tint,
  label,
  sub,
  value,
  pct,
}: {
  icon: ReactNode;
  tint: string;
  label: string;
  sub: string;
  value: string;
  pct: number;
}) {
  return (
    <div style={{ marginBottom: 17 }}>
      <div className="al-row">
        <div className="al-orb" style={{ background: `${tint}22`, color: tint, borderColor: `${tint}33` }}>
          {icon}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="al-between">
            <div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{label}</div>
              <div style={{ fontSize: 10.5, color: "var(--mist-dim)", marginTop: 1 }}>{sub}</div>
            </div>
            <div className="al-num" style={{ color: "var(--paper)" }}>{value}</div>
          </div>
          <div className="al-track">
            <div className="al-fill" style={{ width: `${pct}%`, background: tint }} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Today({
  now,
  pan,
  onUpay,
  onConsult,
  onShare,
}: {
  now: Date;
  pan: Panchang;
  onUpay: () => void;
  onConsult: () => void;
  onShare: () => void;
}) {
  const hour = now.getHours();
  const greet =
    hour < 5 ? "Shubh ratri," : hour < 12 ? "Shubh prabhat," : hour < 17 ? "Shubh dopahar," : "Shubh sandhya,";
  const start = toMins(pan.rahu_kaal.start);
  const end = toMins(pan.rahu_kaal.end);
  const mins = hour * 60 + now.getMinutes() + now.getSeconds() / 60;
  const active = mins >= start && mins < end;
  const delta = active ? end - mins : start > mins ? start - mins : start + 24 * 60 - mins;
  const sunRashi = pan.user.lagna;
  const abStart = toMins(pan.abhijit.start);
  const abEnd = toMins(pan.abhijit.end);
  const abLen = Math.max(1, abEnd - abStart);

  return (
    <>
      <Sky />
      <div style={{ position: "relative" }}>
        <div className="al-rise">
          <div className="al-eyebrow">
            <Sun size={12} /> LAGNA {sunRashi.toUpperCase()}
            <span className="al-deva">· {RASHI_DEVA[sunRashi] ?? sunRashi}</span>
          </div>
          <h1 className="al-h1">
            {greet}
            <em>{firstName(pan.user.name)}</em>
          </h1>
        </div>

        <div
          className="al-card al-card--gold al-rise"
          style={{
            marginTop: 22,
            animationDelay: ".06s",
            borderColor: active ? "rgba(240,169,76,.4)" : "var(--hair-gold)",
          }}
        >
          <div className="al-between">
            <div className="al-row" style={{ gap: 10 }}>
              <div
                className="al-orb"
                style={{
                  background: active ? "rgba(240,169,76,.16)" : "rgba(111,201,166,.14)",
                  color: active ? "var(--saffron)" : "var(--jade)",
                  borderColor: "transparent",
                }}
              >
                {active ? <AlertTriangle size={17} /> : <Check size={17} />}
              </div>
              <div>
                <div className="al-label" style={{ color: active ? "var(--saffron)" : "var(--jade)" }}>
                  {active ? "RAHU KAAL — ACTIVE NOW" : "CLEAR WINDOW"}
                </div>
                <div style={{ fontSize: 13.5, fontWeight: 500, marginTop: 3 }}>
                  {active ? `Ends in ${countdown(delta)}` : `Rahu Kaal in ${countdown(delta)}`}
                </div>
              </div>
            </div>
            <Clock size={15} color="var(--mist-dim)" />
          </div>
          <div style={{ marginTop: 14, paddingTop: 13, borderTop: "1px solid var(--hairline)" }} className="al-between">
            <span className="al-label">
              TODAY · {clock(start)} – {clock(end)}
            </span>
            <span style={{ fontSize: 11, color: "var(--mist)" }}>{pan.now}</span>
          </div>
        </div>

        <div className="al-card al-rise" style={{ marginTop: 14, animationDelay: ".12s" }}>
          <div className="al-between" style={{ marginBottom: 11 }}>
            <h3 className="al-h3">Aaj ka Panchang</h3>
            <button className="al-icobtn" aria-label="Share today's panchang" onClick={onShare}>
              <Share2 size={14} />
            </button>
          </div>
          <p className="al-body">
            <b>Chandra in {pan.nakshatra}</b> pada {pan.pada}. {pan.note}
          </p>
          <div style={{ display: "flex", gap: 8, margin: "14px 0 16px", flexWrap: "wrap" }}>
            {[
              ["Tithi", pan.tithi],
              ["Nakshatra", pan.nakshatra],
              ["Upay", pan.upay_done ? "Done" : "Pending"],
            ].map(([k, v]) => (
              <div
                key={k}
                style={{
                  padding: "7px 11px",
                  borderRadius: 11,
                  background: "var(--surface)",
                  border: "1px solid var(--hairline)",
                }}
              >
                <div className="al-label" style={{ fontSize: 8.5 }}>{k}</div>
                <div style={{ fontSize: 11.5, marginTop: 2, maxWidth: 140 }}>{v}</div>
              </div>
            ))}
          </div>
          <button className="al-pill" onClick={onUpay} disabled={pan.upay_done}>
            {pan.upay_done ? "Upay marked for today" : "Mark today's upay"}
          </button>
        </div>

        <div className="al-rule">
          <span>Din ke Muhurat</span>
          <i />
        </div>
        <Meter
          icon={<Sunrise size={16} />}
          tint="var(--jade)"
          label="Abhijit Muhurat"
          sub={`${clock(abStart)} – ${clock(abEnd)} · best of the day`}
          value={`${abLen}m`}
          pct={pan.abhijit.active ? 90 : 62}
        />
        <Meter
          icon={<Gem size={16} />}
          tint="var(--gold)"
          label="Nitya streak"
          sub={pan.upay}
          value={`${pan.streak}d`}
          pct={Math.min(100, (pan.streak % 21) * (100 / 21))}
        />
        <Meter
          icon={<Moon size={16} />}
          tint="var(--indigo)"
          label="Sunrise / Sunset"
          sub={`${clock(toMins(pan.sunrise))} – ${clock(toMins(pan.sunset))}`}
          value={pan.now}
          pct={Math.min(100, (mins / 1440) * 100)}
        />

        <div className="al-card al-rise" style={{ marginTop: 8, animationDelay: ".2s" }}>
          <div className="al-between">
            <div>
              <div className="al-label">NITYA PANCHANG STREAK</div>
              <div style={{ marginTop: 5 }}>
                <span className="al-num" style={{ color: "var(--gold)" }}>{pan.streak}</span>
                <span style={{ fontSize: 12, color: "var(--mist)", marginLeft: 7 }}>days unbroken</span>
              </div>
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              {Array.from({ length: 7 }).map((_, i) => (
                <div
                  key={i}
                  style={{
                    width: 7,
                    height: 22,
                    borderRadius: 999,
                    background: i < Math.min(7, pan.streak) ? "var(--gold)" : "rgba(255,255,255,.12)",
                    opacity: i < Math.min(7, pan.streak) ? 0.35 + i * 0.11 : 1,
                  }}
                />
              ))}
            </div>
          </div>
        </div>

        <button type="button" className="al-card al-card--gold al-rise" style={{ marginTop: 16, padding: 14, animationDelay: ".22s", width: "100%", textAlign: "left", cursor: "pointer", color: "inherit" }} onClick={onConsult}>
          <div className="al-row" style={{ alignItems: "center" }}>
            <div style={{ width: 56, height: 56, borderRadius: 999, overflow: "hidden", flex: "0 0 auto", boxShadow: "0 0 0 1.5px var(--hair-gold)" }}>
              <Baba size={56} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="al-label">JYOTISH DRISHTI · LIVE</div>
              <div style={{ fontFamily: "var(--serif)", fontSize: 20, fontWeight: 600, marginTop: 2 }}>Acharya Kaushik</div>
              <div style={{ fontSize: 11, color: "var(--mist)", marginTop: 2 }}>Vedic & Prashna · ₹25/min</div>
            </div>
            <div className="al-orb" style={{ background: "var(--gold)", color: "#1A1206", borderColor: "transparent" }}>
              <MessageSquare size={16} />
            </div>
          </div>
        </button>
      </div>
    </>
  );
}

function ChartTab({
  pack,
  onBack,
}: {
  pack: { chart: NatalChart; name: string; place: string; dob: string; tob: string };
  onBack: () => void;
}) {
  const [style, setStyle] = useState("North");
  const lead: Array<{ pos: ChartPos; tint: string; icon: ReactNode }> = [];
  const sun = pack.chart.positions.find((p) => p.graha === "Sun");
  const moon = pack.chart.positions.find((p) => p.graha === "Moon");
  if (sun) lead.push({ pos: sun, tint: "var(--gold)", icon: <Sun size={15} /> });
  if (moon) lead.push({ pos: moon, tint: "var(--indigo)", icon: <Moon size={15} /> });
  const lagnaPos = pack.chart.positions[0];
  return (
    <>
      <ScreenBack onBack={onBack} label="Today" />
      <div className="al-between" style={{ marginBottom: 6, gap: 12 }}>
        <h2 className="al-h2">Aapki Kundali</h2>
        <span className="al-label">
          {pack.chart.mangal.status === "clear" ? "MANGAL CLEAR" : `MANGAL ${pack.chart.mangal.status.toUpperCase()}`}
        </span>
      </div>
      <div className="al-label" style={{ marginBottom: 16 }}>
        {fmtDob(pack.dob)} · {pack.tob} · {pack.place.toUpperCase()}
      </div>

      <div className="al-rise">
        <Kundali chart={pack.chart} />
      </div>

      <div className="al-seg al-rise" style={{ marginTop: 14, animationDelay: ".08s" }}>
        {["North", "South", "Navamsa"].map((s) => (
          <button key={s} data-on={style === s} onClick={() => setStyle(s)}>
            {s}
          </button>
        ))}
      </div>

      <div className="al-rule">
        <span>Graha Sthiti</span>
        <i />
      </div>

      <div className="al-card al-rise" style={{ marginBottom: 10, padding: 15 }}>
        <div className="al-row">
          <div className="al-orb" style={{ color: "var(--lotus)" }}>
            <Compass size={15} />
          </div>
          <div style={{ flex: 1 }}>
            <div className="al-label">LAGNA</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 9, marginTop: 2 }}>
              <span style={{ fontFamily: "var(--serif)", fontSize: 22, fontWeight: 500 }}>{pack.chart.lagna}</span>
              <span style={{ fontSize: 11, color: "var(--mist-dim)" }}>{pack.chart.lagna_en}</span>
            </div>
          </div>
          <span
            style={{
              fontSize: 10.5,
              color: "var(--gold)",
              padding: "4px 9px",
              borderRadius: 8,
              background: "rgba(233,206,142,.09)",
              border: "1px solid var(--hair-gold)",
            }}
          >
            1st house
          </span>
        </div>
      </div>

      {lead.map((g, i) => (
        <div key={g.pos.graha} className="al-card al-rise" style={{ marginBottom: 10, padding: 15, animationDelay: `${0.1 + i * 0.06}s` }}>
          <div className="al-row">
            <div className="al-orb" style={{ color: g.tint }}>
              {g.icon}
            </div>
            <div style={{ flex: 1 }}>
              <div className="al-label">{g.pos.graha.toUpperCase()}</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 9, marginTop: 2 }}>
                <span style={{ fontFamily: "var(--serif)", fontSize: 22, fontWeight: 500 }}>{g.pos.rashi}</span>
                <span style={{ fontSize: 11, color: "var(--mist-dim)", letterSpacing: ".04em" }}>{g.pos.dms}</span>
              </div>
            </div>
            <span
              style={{
                fontSize: 10.5,
                color: "var(--gold)",
                padding: "4px 9px",
                borderRadius: 8,
                background: "rgba(233,206,142,.09)",
                border: "1px solid var(--hair-gold)",
              }}
            >
              {g.pos.house}
              {g.pos.house === 1 ? "st" : g.pos.house === 2 ? "nd" : g.pos.house === 3 ? "rd" : "th"} house
            </span>
          </div>
        </div>
      ))}

      {lagnaPos && (
        <div className="al-card al-card--gold al-rise" style={{ marginTop: 16, animationDelay: ".3s" }}>
          <div className="al-label">AYANAMSHA · LAHIRI</div>
          <div style={{ fontFamily: "var(--serif)", fontSize: 21, marginTop: 6 }}>
            {pack.chart.ayanamsha.toFixed(2)}° <span style={{ color: "var(--mist-dim)" }}>·</span> {pack.chart.nakshatra} Chandra
          </div>
          <p className="al-body" style={{ marginTop: 8 }}>
            Whole-sign houses from {pack.chart.lagna} Lagna. North Indian diamond is the working chart.
          </p>
        </div>
      )}
    </>
  );
}

function MelapakTab({
  match,
  hostName,
  copied,
  onShare,
  onBack,
}: {
  match: MatchResult | null;
  hostName: string;
  copied: boolean;
  onShare: (mode: string) => void;
  onBack?: () => void;
}) {
  const [mode, setMode] = useState<(typeof MODE_KEYS)[number]["k"]>("bandhan");
  if (!match) {
    return (
      <>
        {onBack ? <ScreenBack onBack={onBack} label="Today" /> : null}
        <p className="al-body">Computing Ashtakoot…</p>
      </>
    );
  }
  const nadi = match.koots.find((k) => k.name === "Nadi");
  const bhakoot = match.koots.find((k) => k.name === "Bhakoot");
  const quote =
    (bhakoot?.score ?? 7) === 0
      ? "Strong minds, split households — the friction here is family, not feeling."
      : match.verdict === "excellent"
        ? "The stars agree more than they quarrel. This is a workable Bandhan."
        : "Enough gunas to proceed — read the weak koots before you promise a household.";

  return (
    <>
      {onBack ? <ScreenBack onBack={onBack} label="Today" /> : null}
      <div className="al-between" style={{ marginBottom: 20 }}>
        <div className="al-label">PRIVATE MATCH</div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="al-icobtn" aria-label="Save match">
            <Heart size={14} />
          </button>
          <button className="al-icobtn" aria-label="Share match" onClick={() => onShare(mode)}>
            <Share2 size={14} />
          </button>
        </div>
      </div>

      <div className="al-rise">
        <ScoreRing score={match.gunas} max={match.max} />
        <div style={{ textAlign: "center", marginTop: 14 }}>
          <div style={{ fontFamily: "var(--serif)", fontSize: 27, fontWeight: 500 }}>
            {firstName(match.a.name || hostName)} <span style={{ color: "var(--gold-deep)" }}>×</span> {firstName(match.b.name)}
          </div>
          <div className="al-label" style={{ marginTop: 5 }}>ASHTAKOOT GUNA MILAN</div>
        </div>
      </div>

      <div className="al-seg al-rise" style={{ marginTop: 20, animationDelay: ".08s" }}>
        {MODE_KEYS.map((m) => (
          <button key={m.k} data-on={mode === m.k} onClick={() => setMode(m.k)}>
            {m.label}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
        {[
          { l: "NADI DOSHA", v: (nadi?.score ?? 0) === 8 ? "Absent" : "Present", c: (nadi?.score ?? 0) === 8 ? "var(--jade)" : "var(--saffron)" },
          {
            l: "MANGAL DOSHA",
            v: match.mangal === "clear" ? "Absent" : match.mangal === "cancelled" ? "Cancelled" : "Present",
            c: match.mangal === "clear" || match.mangal === "cancelled" ? "var(--jade)" : "var(--saffron)",
          },
        ].map((s) => (
          <div key={s.l} className="al-card al-rise" style={{ flex: 1, padding: 15, animationDelay: ".14s" }}>
            <div className="al-label" style={{ fontSize: 8.5 }}>{s.l}</div>
            <div className="al-row" style={{ gap: 7, marginTop: 7 }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: s.c }} />
              <span style={{ fontFamily: "var(--serif)", fontSize: 19, fontWeight: 500 }}>{s.v}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="al-card al-rise" style={{ marginTop: 16, animationDelay: ".2s" }}>
        <p className="al-quote">{quote}</p>
        <p className="al-body" style={{ marginTop: 12 }}>
          {match.a.nakshatra} × {match.b.nakshatra}. Verdict: {match.verdict}.
          Only the two of you can open a Melapak link — it never posts publicly.
        </p>
      </div>

      <div className="al-rule">
        <span>Eight Koots</span>
        <i />
      </div>

      {match.koots.map((k, i) => (
        <div key={k.name} className="al-rise" style={{ marginBottom: 13, animationDelay: `${0.24 + i * 0.04}s` }}>
          <div className="al-between">
            <div>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{k.name}</span>
              <div style={{ fontSize: 10, color: "var(--mist-dim)", marginTop: 1 }}>{KOOT_NOTE[k.name] ?? ""}</div>
            </div>
            <span
              style={{
                fontFamily: "var(--serif)",
                fontSize: 17,
                fontWeight: 600,
                color: k.score === 0 ? "var(--saffron)" : "var(--paper)",
              }}
            >
              {k.score}
              <span style={{ color: "var(--mist-dim)", fontSize: 12 }}>/{k.max}</span>
            </span>
          </div>
          <div className="al-track">
            <div
              className="al-fill"
              style={{
                width: `${(k.score / k.max) * 100}%`,
                background: k.score === 0 ? "var(--saffron)" : k.score === k.max ? "var(--jade)" : "var(--gold)",
              }}
            />
          </div>
        </div>
      ))}

      <button className="al-pill" style={{ marginTop: 18 }} onClick={() => onShare(mode)}>
        <Share2 size={15} /> {copied ? "Link copied" : "Send report on WhatsApp"}
      </button>
      <p style={{ fontSize: 10.5, color: "var(--mist-dim)", textAlign: "center", marginTop: 10 }}>
        Only you and {firstName(match.b.name)} can open this link.
      </p>
    </>
  );
}

function SamadhanTab({
  items,
  booked,
  onBook,
  onBack,
}: {
  items: SamadhanItem[];
  booked: string | null;
  onBook: (id: string) => void;
  onBack: () => void;
}) {
  const gem = items.find((i) => i.kind === "gem");
  const pujas = items.filter((i) => i.kind !== "gem");
  return (
    <>
      <ScreenBack onBack={onBack} label="Today" />
      <h2 className="al-h2" style={{ marginBottom: 4 }}>Samadhan</h2>
      <p className="al-body" style={{ marginBottom: 18 }}>
        Remedies matched to what your chart is actually running right now.
      </p>

      {gem && (
        <div className="al-card al-card--gold al-rise">
          <div className="al-label">SUGGESTED FOR YOU</div>
          <div style={{ fontFamily: "var(--serif)", fontSize: 22, marginTop: 6, lineHeight: 1.2 }}>{gem.title}</div>
          <p className="al-body" style={{ marginTop: 9 }}>{gem.perks[0]}</p>
          <div className="al-between" style={{ marginTop: 15 }}>
            <div>
              <span style={{ fontFamily: "var(--serif)", fontSize: 25, fontWeight: 600 }}>
                ₹{gem.price.toLocaleString("en-IN")}
              </span>
              <span style={{ fontSize: 11, color: "var(--mist-dim)", marginLeft: 8 }}>{gem.place}</span>
            </div>
            <Gem size={20} color="var(--gold)" />
          </div>
          <button className="al-pill" style={{ marginTop: 14 }} onClick={() => onBook(gem.id)} disabled={booked === gem.id}>
            {booked === gem.id ? "Order queued" : gem.cta}
          </button>
        </div>
      )}

      <div className="al-rule">
        <span>Verified Temple Pujas</span>
        <i />
      </div>

      {pujas.map((it, i) => (
        <div key={it.id} className="al-card al-rise" style={{ marginBottom: 11, padding: 16, animationDelay: `${0.08 + i * 0.07}s` }}>
          <div className="al-row" style={{ alignItems: "flex-start" }}>
            <div className="al-orb" style={{ background: "rgba(255,255,255,.05)", color: "var(--saffron)" }}>
              <Flame size={15} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="al-between">
                <span style={{ fontFamily: "var(--serif)", fontSize: 18, fontWeight: 600 }}>{it.title}</span>
                <span
                  style={{
                    fontSize: 8.5,
                    letterSpacing: ".14em",
                    color: "var(--gold)",
                    padding: "3px 7px",
                    borderRadius: 6,
                    background: "rgba(233,206,142,.09)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {it.kind === "puja" ? "VIDEO PROOF" : "LAB CERT"}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "var(--mist-dim)", marginTop: 3 }}>{it.place}</div>
              <p className="al-body" style={{ fontSize: 12, marginTop: 8 }}>{it.perks[0]}</p>
              <div className="al-between" style={{ marginTop: 12 }}>
                <span style={{ fontFamily: "var(--serif)", fontSize: 19, fontWeight: 600 }}>
                  ₹{it.price.toLocaleString("en-IN")}
                </span>
                <button
                  className="al-pill al-ghost"
                  style={{ width: "auto", padding: "8px 16px", fontSize: 12 }}
                  onClick={() => onBook(it.id)}
                  disabled={booked === it.id}
                >
                  <Play size={12} /> {booked === it.id ? "Queued" : "Book slot"}
                </button>
              </div>
            </div>
          </div>
        </div>
      ))}
    </>
  );
}

function ScreenBack({
  onBack,
  label,
}: {
  onBack: () => void;
  label?: string;
}) {
  return (
    <div className="al-backrow">
      <button type="button" className="al-icobtn" onClick={onBack} aria-label="Back">
        <ChevronLeft size={16} />
      </button>
      {label ? <span className="al-back-lbl">{label}</span> : null}
    </div>
  );
}

function ChatSheet({
  onClose,
  onBack,
  expanded,
  onToggleExpand,
}: {
  onClose: () => void;
  onBack: () => void;
  expanded: boolean;
  onToggleExpand: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState("");
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .chatStart("ak")
      .then((res) => {
        if (!cancelled) setMessages(res.messages);
      })
      .catch((e: unknown) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Could not open consult");
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = async () => {
    const text = draft.trim();
    if (!text || busy || text.length > 2000) return;
    setDraft("");
    setBusy(true);
    setErr("");
    setMessages((m) => [...m, { id: Date.now(), role: "user", content: text, created_at: "" }]);
    try {
      const res = await api.chatSend("ak", text);
      setMessages(res.messages);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Reply failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`al-bot-panel${expanded ? " is-full" : ""}`} role="dialog" aria-label="Chat with Acharya Kaushik">
      <header className="al-bot-head">
        <div className="al-row">
          <button type="button" className="al-icobtn" onClick={onBack} aria-label="Back to app">
            <ChevronLeft size={16} />
          </button>
          <div className="al-bot-avatar">
            <Baba size={44} />
          </div>
          <div>
            <div className="al-bot-name">Acharya Kaushik</div>
            <div className="al-label" style={{ color: "var(--jade)" }}>
              ● AVAILABLE NOW
            </div>
          </div>
        </div>
        <div className="al-bot-actions">
          <button
            type="button"
            className="al-icobtn"
            onClick={onToggleExpand}
            aria-label={expanded ? "Shrink widget" : "Expand widget"}
          >
            {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
          <button type="button" className="al-icobtn" onClick={onClose} aria-label="Hide chat">
            <X size={14} />
          </button>
        </div>
      </header>
      <div className="al-bot-msgs">
        {messages.map((m) => (
          <div
            key={m.id}
            className="al-bot-line"
            data-me={m.role === "user" ? "true" : "false"}
          >
            {m.role !== "user" && (
              <div className="al-bot-mini">
                <Baba size={28} />
              </div>
            )}
            <div className={m.role === "user" ? "al-bubble al-bubble--me" : "al-bubble al-bubble--them"}>{m.content}</div>
          </div>
        ))}
        {busy && (
          <div className="al-row" style={{ color: "var(--mist-dim)", fontSize: 12, gap: 8 }}>
            <Loader2 size={14} className="al-spin" />
            Reading your kundali…
          </div>
        )}
        {err && <p className="al-err">{err}</p>}
        <div ref={bottom} />
      </div>
      <form
        className="al-bot-form"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          className="al-input"
          placeholder="Ask about muhurat, dosha, career…"
          value={draft}
          maxLength={2000}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" className="al-pill al-bot-send" disabled={busy || !draft.trim()} aria-label="Send">
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}

type BirthForm = { name: string; dob: string; tob: string; place: string };

function BirthFields({
  value,
  onChange,
  cities,
}: {
  value: BirthForm;
  onChange: (v: BirthForm) => void;
  cities: City[];
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <input className="al-input" placeholder="Your name" value={value.name} onChange={(e) => onChange({ ...value, name: e.target.value })} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <input className="al-input" type="date" value={value.dob} onChange={(e) => onChange({ ...value, dob: e.target.value })} />
        <input className="al-input" type="time" value={value.tob} onChange={(e) => onChange({ ...value, tob: e.target.value })} />
      </div>
      <select className="al-select" value={value.place} onChange={(e) => onChange({ ...value, place: e.target.value })}>
        {cities.map((c) => (
          <option key={c.name} value={c.name}>
            {c.name}
          </option>
        ))}
      </select>
    </div>
  );
}

function AccountMenu({
  me,
  onClose,
  onAskLogout,
  onMe,
}: {
  me: SessionUser | null;
  onClose: () => void;
  onAskLogout: () => void;
  onMe: (user: SessionUser) => void;
}) {
  const [totpStep, setTotpStep] = useState<"idle" | "setup" | "recovery" | "disable">("idle");
  const [setup, setSetup] = useState<{ qr: string; secret: string } | null>(null);
  const [code, setCode] = useState("");
  const [recovery, setRecovery] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const startSetup = async () => {
    setBusy(true);
    setErr("");
    try {
      const data = await api.totpSetup();
      setSetup({ qr: data.qr, secret: data.secret });
      setTotpStep("setup");
      setCode("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not start authenticator setup.");
    } finally {
      setBusy(false);
    }
  };

  const confirmEnable = async () => {
    setBusy(true);
    setErr("");
    try {
      const data = await api.totpEnable(code);
      setRecovery(data.recovery_codes);
      setTotpStep("recovery");
      if (me) onMe({ ...me, totp_enabled: true });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not enable authenticator.");
    } finally {
      setBusy(false);
    }
  };

  const confirmDisable = async () => {
    setBusy(true);
    setErr("");
    try {
      await api.totpDisable(code);
      setTotpStep("idle");
      setCode("");
      if (me) onMe({ ...me, totp_enabled: false });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not turn off authenticator.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="al-account" role="menu" aria-label="Account">
      <div className="al-label">SIGNED IN</div>
      <div className="al-account-name">{me?.name || "Guest"}</div>
      <div className="al-account-mail">
        <Mail size={12} />
        {me?.email || "Session on this device"}
      </div>
      {me?.lagna && (
        <div className="al-account-meta">
          Lagna {me.lagna}
          {me.nakshatra ? ` · ${me.nakshatra}` : ""}
          {me.place ? ` · ${me.place}` : ""}
        </div>
      )}
      <p className="al-body" style={{ margin: "12px 0 0", fontSize: 12 }}>
        This device holds a 30-day httpOnly session. Logging out deletes it on the server; the next visit needs a fresh email code.
      </p>
      <div className="al-totp">
        <div className="al-label" style={{ marginTop: 16 }}>
          AUTHENTICATOR
        </div>
        {totpStep === "idle" && (
          <>
            <p className="al-body" style={{ marginTop: 8, fontSize: 12 }}>
              {me?.totp_enabled
                ? "A second code from your authenticator app is required after email."
                : "Optional. After email, ask for a code from an authenticator app."}
            </p>
            {me?.totp_enabled ? (
              <button
                type="button"
                className="al-ghost"
                style={{ marginTop: 12 }}
                onClick={() => {
                  setTotpStep("disable");
                  setCode("");
                  setErr("");
                }}
              >
                Turn off authenticator
              </button>
            ) : (
              <button type="button" className="al-ghost" style={{ marginTop: 12 }} onClick={() => void startSetup()} disabled={busy}>
                {busy ? "Preparing…" : "Protect with authenticator"}
              </button>
            )}
          </>
        )}
        {totpStep === "setup" && setup && (
          <>
            <img className="al-totp-qr" src={setup.qr} alt="Authenticator QR code" />
            <p className="al-body" style={{ fontSize: 12, marginTop: 8 }}>
              Scan in your authenticator app, or enter this key: <code className="al-totp-secret">{setup.secret}</code>
            </p>
            <input
              className="al-input"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="6-digit app code"
              value={code}
              maxLength={6}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            />
            <button className="al-pill" style={{ marginTop: 12 }} onClick={() => void confirmEnable()} disabled={busy || code.length !== 6}>
              {busy ? "Checking…" : "Enable authenticator"}
            </button>
            <button type="button" className="al-textbtn" style={{ marginTop: 8, width: "100%", justifyContent: "center" }} onClick={() => setTotpStep("idle")}>
              Cancel
            </button>
          </>
        )}
        {totpStep === "recovery" && recovery && (
          <>
            <p className="al-body" style={{ fontSize: 12, marginTop: 8 }}>
              Save these recovery codes now. They will not be shown again.
            </p>
            <ul className="al-totp-codes">
              {recovery.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <button type="button" className="al-pill" style={{ marginTop: 12 }} onClick={() => setTotpStep("idle")}>
              I have saved these codes
            </button>
          </>
        )}
        {totpStep === "disable" && (
          <>
            <p className="al-body" style={{ fontSize: 12, marginTop: 8 }}>
              Enter a current authenticator code or a recovery code.
            </p>
            <input
              className="al-input"
              autoComplete="one-time-code"
              placeholder="App or recovery code"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
            />
            <button className="al-pill al-pill--danger" style={{ marginTop: 12 }} onClick={() => void confirmDisable()} disabled={busy || code.length < 6}>
              {busy ? "Turning off…" : "Disable authenticator"}
            </button>
            <button type="button" className="al-textbtn" style={{ marginTop: 8, width: "100%", justifyContent: "center" }} onClick={() => setTotpStep("idle")}>
              Cancel
            </button>
          </>
        )}
        {err && <p className="al-err">{err}</p>}
      </div>
      <button type="button" className="al-pill al-pill--danger" style={{ marginTop: 16 }} onClick={onAskLogout}>
        <LogOut size={15} /> Log out
      </button>
      <button type="button" className="al-textbtn" style={{ marginTop: 10, width: "100%", justifyContent: "center" }} onClick={onClose}>
        Close
      </button>
    </div>
  );
}

function LogoutWindow({
  email,
  busy,
  onStay,
  onConfirm,
}: {
  email: string;
  busy: boolean;
  onStay: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="al-logout-win" role="dialog" aria-modal="true" aria-labelledby="logout-title">
      <button type="button" className="al-scrim" aria-label="Cancel logout" onClick={onStay} />
      <div className="al-logout-card">
        <div className="al-eyebrow">END SESSION</div>
        <h2 id="logout-title" className="al-h2" style={{ marginTop: 8 }}>
          Log out of AstroLive?
        </h2>
        <p className="al-body" style={{ marginTop: 10 }}>
          {email
            ? `You will need a new code at ${email} to open this kundali again.`
            : "You will need a new email code to open this kundali again."}
        </p>
        <div className="al-logout-actions">
          <button type="button" className="al-ghost" onClick={onStay} disabled={busy}>
            Stay signed in
          </button>
          <button type="button" className="al-pill al-pill--danger" onClick={onConfirm} disabled={busy}>
            {busy ? "Signing out…" : "Log out"}
          </button>
        </div>
      </div>
    </div>
  );
}

function AuthScreen() {
  const navigate = useNavigate();
  const [session, setSessionState] = useState<"wait" | "in" | "out">("wait");
  const [step, setStep] = useState<"email" | "code" | "totp" | "profile">("email");
  const [cities, setCities] = useState<City[]>([]);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [ticket, setTicket] = useState("");
  const [form, setForm] = useState<BirthForm>({ name: "", dob: "2002-06-21", tob: "10:30", place: "Delhi" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [retryIn, setRetryIn] = useState(0);

  useEffect(() => {
    api
      .me()
      .then(() => setSessionState("in"))
      .catch(() => setSessionState("out"));
    api.cities().then(setCities).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (retryIn <= 0) return;
    const id = window.setTimeout(() => setRetryIn((n) => Math.max(0, n - 1)), 1000);
    return () => window.clearTimeout(id);
  }, [retryIn]);

  if (session === "wait") {
    return (
      <div className="al">
        <div className="al-stage al-stage--auth">
          <p className="al-body al-auth-wait">Opening your sky…</p>
        </div>
      </div>
    );
  }
  if (session === "in") return <Navigate to="/" replace />;

  const sendCode = async () => {
    const mail = email.trim().toLowerCase();
    if (!mail.includes("@") || !mail.includes(".")) {
      setErr("Enter a valid email address.");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const res = await api.sendOtp(mail);
      setEmail(mail);
      setCode("");
      setStep("code");
      setRetryIn(res.retry_after || 60);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not send the code");
    } finally {
      setBusy(false);
    }
  };

  const checkCode = async () => {
    const digits = code.replace(/\D/g, "");
    if (digits.length !== 6) {
      setErr("Enter the 6-digit code from your email.");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const res = await api.verifyOtp(email, digits);
      if (res.needs_profile) {
        setTicket(res.ticket ?? "");
        setStep("profile");
        return;
      }
      if (res.needs_totp) {
        setCode("");
        setStep("totp");
        return;
      }
      navigate("/", { replace: true });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not verify the code");
    } finally {
      setBusy(false);
    }
  };

  const checkTotp = async () => {
    if (code.trim().length < 6) {
      setErr("Enter the authenticator or recovery code.");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      await api.verifyTotp(code.trim());
      navigate("/", { replace: true });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not verify authenticator");
    } finally {
      setBusy(false);
    }
  };

  const finishProfile = async () => {
    if (form.name.trim().length < 2) {
      setErr("Name must be at least 2 characters.");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      await api.register({ ...form, ticket });
      navigate("/", { replace: true });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not create account");
    } finally {
      setBusy(false);
    }
  };

  const title =
    step === "email"
      ? "Your sky, after a code."
      : step === "code"
        ? "Check your inbox."
        : step === "totp"
          ? "Open your authenticator."
          : "Three fields. Then the sky.";
  const blurb =
    step === "email"
      ? "Enter the email you use. We send a 6-digit code — no password to remember."
      : step === "code"
        ? `We emailed a code to ${email}. It expires in 10 minutes.`
        : step === "totp"
          ? "This account asks for a second code from your authenticator app, or a recovery code."
          : "Date, time, and place of birth. Lagna, Chandra and today's muhurat in the first twelve seconds.";

  return (
    <div className="al">
      <div className="al-stage al-stage--auth">
        <div className="al-auth">
          <div className="al-auth-brand">
            <Sky />
            <div className="al-eyebrow">VEDIC DECISION ENGINE</div>
            <h1 className="al-h1">
              AstroLive.<em>{title}</em>
            </h1>
            <p className="al-auth-lead">Your sky, after a code.</p>
            <p className="al-auth-rail">
              No password. A six-digit email code lasts ten minutes. After that, this device keeps a 30-day session you can end from the three-dot menu.
            </p>
          </div>
          <div className="al-auth-form">
            {step !== "email" && (
              <ScreenBack
                onBack={() => {
                  if (step === "profile" || step === "totp") {
                    setStep("code");
                    setCode("");
                  } else {
                    setStep("email");
                  }
                  setErr("");
                }}
                label={step === "code" ? "Email" : "Code"}
              />
            )}
            <p className="al-body al-auth-blurb">{blurb}</p>
            <div className="al-auth-fields">
              {step === "email" && (
                <input
                  className="al-input"
                  type="email"
                  autoComplete="email"
                  placeholder="you@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void sendCode();
                  }}
                />
              )}
              {step === "code" && (
                <input
                  className="al-input"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="6-digit code"
                  value={code}
                  maxLength={6}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void checkCode();
                  }}
                />
              )}
              {step === "totp" && (
                <input
                  className="al-input"
                  autoComplete="one-time-code"
                  placeholder="Authenticator or recovery code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void checkTotp();
                  }}
                />
              )}
              {step === "profile" && <BirthFields value={form} onChange={setForm} cities={cities} />}
            </div>
            {err && <p className="al-err">{err}</p>}
            {step === "email" && (
              <button className="al-pill" onClick={() => void sendCode()} disabled={busy}>
                {busy ? "Sending code…" : "Send code to email"}
              </button>
            )}
            {step === "code" && (
              <>
                <button className="al-pill" onClick={() => void checkCode()} disabled={busy || code.length !== 6}>
                  {busy ? "Checking…" : "Verify code"}
                </button>
                <button type="button" className="al-textbtn" onClick={() => void sendCode()} disabled={busy || retryIn > 0}>
                  {retryIn > 0 ? `Resend in ${retryIn}s` : "Resend code"}
                </button>
                <button
                  type="button"
                  className="al-textbtn"
                  onClick={() => {
                    setStep("email");
                    setCode("");
                    setErr("");
                  }}
                >
                  Use a different email
                </button>
              </>
            )}
            {step === "totp" && (
              <button className="al-pill" onClick={() => void checkTotp()} disabled={busy || code.trim().length < 6}>
                {busy ? "Checking…" : "Verify authenticator"}
              </button>
            )}
            {step === "profile" && (
              <button className="al-pill" onClick={() => void finishProfile()} disabled={busy}>
                {busy ? "Computing natal chart…" : "Open my panchang"}
              </button>
            )}
          </div>
          <details className="al-auth-notes">
            <summary>How sign-in works</summary>
            <p>
              No password. We email a 6-digit code that expires in ten minutes. After you verify, this device keeps a 30-day session. You can add an authenticator later from the account menu.
            </p>
          </details>
        </div>
      </div>
    </div>
  );
}

function HomeApp({ onLogout }: { onLogout: () => void }) {
  const now = useClock();
  const location = useLocation();
  const navigate = useNavigate();
  const tab = pathToTab(location.pathname);
  const [pan, setPan] = useState<Panchang | null>(null);
  const [pack, setPack] = useState<{ chart: NatalChart; name: string; place: string; dob: string; tob: string } | null>(null);
  const [match, setMatch] = useState<MatchResult | null>(null);
  const [items, setItems] = useState<SamadhanItem[]>([]);
  const [booked, setBooked] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [chat, setChat] = useState(false);
  const [chatFull, setChatFull] = useState(false);
  const [toast, setToast] = useState("");
  const [loadErr, setLoadErr] = useState("");
  const [me, setMe] = useState<SessionUser | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [logoutAsk, setLogoutAsk] = useState(false);
  const [logoutBusy, setLogoutBusy] = useState(false);

  useEffect(() => {
    const p = location.pathname;
    if (p === "/" || p === "/kundali" || p === "/melapak" || p === "/samadhan") return;
    navigate("/", { replace: true });
  }, [location.pathname, navigate]);

  const fail = (e: unknown, fallback: string) => {
    if (isAuthError(e)) {
      onLogout();
      navigate("/login", { replace: true });
      return;
    }
    setToast(e instanceof Error ? e.message : fallback);
    setTimeout(() => setToast(""), 3200);
  };

  const refreshPan = () => {
    api
      .panchang()
      .then((data) => {
        setPan(data);
        setLoadErr("");
      })
      .catch((e: unknown) => {
        if (isAuthError(e)) {
          onLogout();
          navigate("/login", { replace: true });
          return;
        }
        setLoadErr(e instanceof Error ? e.message : "Could not load panchang.");
      });
  };

  useEffect(() => {
    refreshPan();
    const id = setInterval(refreshPan, 30_000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    api.demoPriya().then(setMatch).catch((e: unknown) => fail(e, "Could not load match."));
    api.samadhan().then(setItems).catch((e: unknown) => fail(e, "Could not load offerings."));
    api.kundali().then(setPack).catch((e: unknown) => fail(e, "Could not load kundali."));
    api.me().then(setMe).catch((e: unknown) => fail(e, "Could not load account."));
  }, []);

  const logout = async () => {
    setLogoutBusy(true);
    try {
      await api.logout();
    } catch {
      clearSession();
    }
    onLogout();
    navigate("/login", { replace: true });
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (logoutAsk) setLogoutAsk(false);
      else setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [logoutAsk]);

  const share = async (mode: string) => {
    try {
      const link = await api.createLink(mode);
      const url = `${window.location.origin}${link.path}`;
      try {
        await navigator.clipboard.writeText(url);
      } catch {
        setToast(url);
        setTimeout(() => setToast(""), 4000);
        return;
      }
      setCopied(true);
      setToast("Link copied — paste into WhatsApp");
      setTimeout(() => {
        setCopied(false);
        setToast("");
      }, 2400);
    } catch (e) {
      fail(e, "Could not create share link.");
    }
  };

  return (
    <div className="al">
      <div className="al-stage">
        <div className="al-rack">
          <aside className="al-rail al-rail--left">
            <button
              type="button"
              className="al-dots al-dots--rail"
              aria-label="Open account menu"
              aria-expanded={menuOpen}
              onClick={() => {
                setMenuOpen(true);
                setLogoutAsk(false);
              }}
            >
              <MoreVertical size={20} />
            </button>
            <div className="al-rail-card">
              <div className="al-label">ACCOUNT</div>
              <div className="al-account-name">{me?.name || pan?.user.name || "Signed in"}</div>
              <div className="al-account-mail">
                <Mail size={12} />
                {me?.email || "Session on this device"}
              </div>
              <p className="al-body" style={{ marginTop: 10, fontSize: 12 }}>
                Three dots open your session. Log out when you leave a shared screen.
              </p>
              <button
                type="button"
                className="al-textbtn"
                style={{ marginTop: 12 }}
                onClick={() => {
                  setMenuOpen(true);
                  setLogoutAsk(false);
                }}
              >
                Open account menu
              </button>
            </div>
          </aside>
          <div className="al-phone">
            <header className="al-chrome">
              <div className="al-chrome-cluster">
                <button
                  type="button"
                  className="al-dots"
                  aria-label="Open account menu"
                  aria-expanded={menuOpen}
                  onClick={() => {
                    setMenuOpen((o) => !o);
                    setLogoutAsk(false);
                  }}
                >
                  <MoreVertical size={18} />
                </button>
                {tab !== "today" && (
                  <button type="button" className="al-dots" aria-label="Back to today" onClick={() => navigate("/")}>
                    <ChevronLeft size={18} />
                  </button>
                )}
              </div>
            </header>
            {menuOpen && !logoutAsk && (
              <>
                <button type="button" className="al-scrim" aria-label="Close account menu" onClick={() => setMenuOpen(false)} />
                <AccountMenu
                  me={me}
                  onMe={setMe}
                  onClose={() => setMenuOpen(false)}
                  onAskLogout={() => {
                    setMenuOpen(false);
                    setLogoutAsk(true);
                  }}
                />
              </>
            )}
            {logoutAsk && (
              <LogoutWindow
                email={me?.email || ""}
                busy={logoutBusy}
                onStay={() => setLogoutAsk(false)}
                onConfirm={() => void logout()}
              />
            )}
            <div className="al-scroll" key={tab}>
              {loadErr && <p className="al-err">{loadErr}</p>}
              {tab === "today" && pan && (
                <Today
                  now={now}
                  pan={pan}
                  onUpay={async () => {
                    try {
                      await api.completeUpay();
                      refreshPan();
                    } catch (e) {
                      fail(e, "Could not mark upay complete.");
                    }
                  }}
                  onConsult={() => setChat(true)}
                  onShare={() => void share("mitra")}
                />
              )}
              {tab === "today" && !pan && !loadErr && <p className="al-body">Reading today&apos;s sky…</p>}
              {tab === "chart" && pack && <ChartTab pack={pack} onBack={() => navigate("/")} />}
              {tab === "chart" && !pack && !loadErr && <p className="al-body">Drawing your kundali…</p>}
              {tab === "melapak" && (
                <MelapakTab match={match} hostName={pan?.user.name ?? ""} copied={copied} onShare={(m) => void share(m)} onBack={() => navigate("/")} />
              )}
              {tab === "samadhan" && (
                <SamadhanTab
                  items={items}
                  booked={booked}
                  onBook={async (id) => {
                    try {
                      await api.book(id);
                      setBooked(id);
                      setToast("Sankalp queued");
                      setTimeout(() => setToast(""), 2400);
                      refreshPan();
                    } catch (e) {
                      fail(e, "Could not book this offering.");
                    }
                  }}
                  onBack={() => navigate("/")}
                />
              )}
            </div>
            <nav className="al-nav" aria-label="Primary">
              {TABS.map((t) => {
                const Icon = t.icon;
                return (
                  <button
                    key={t.k}
                    type="button"
                    data-on={tab === t.k}
                    onClick={() => navigate(TAB_PATH[t.k])}
                    aria-label={t.label}
                    aria-current={tab === t.k ? "page" : undefined}
                  >
                    <Icon size={18} />
                    <span className="al-nav-lbl">{t.label}</span>
                  </button>
                );
              })}
            </nav>
            {chat && (
              <ChatSheet
                expanded={chatFull}
                onToggleExpand={() => setChatFull((v) => !v)}
                onBack={() => {
                  if (chatFull) setChatFull(false);
                  else {
                    setChat(false);
                    setChatFull(false);
                  }
                }}
                onClose={() => {
                  setChat(false);
                  setChatFull(false);
                }}
              />
            )}
            <button
              type="button"
              className="al-fab"
              onClick={() => {
                setChat((open) => {
                  if (open) setChatFull(false);
                  return !open;
                });
              }}
              aria-label={chat ? "Hide Acharya Kaushik" : "Talk to Acharya Kaushik"}
              aria-expanded={chat}
            >
              <Baba size={64} />
              <span className="al-fab-badge">
                {chat ? <X size={10} /> : <MessageSquare size={10} />}
              </span>
            </button>
            {toast && (
              <div className="al-toast">
                {toast}
              </div>
            )}
          </div>
          <aside className="al-rail al-rail--right">
            <div className="al-rail-card">
              <div className="al-label">THIS SESSION</div>
              <div className="al-account-name" style={{ fontSize: 22 }}>
                {pan?.user.lagna || me?.lagna || "—"} Lagna
              </div>
              <div className="al-account-meta">
                {pan?.user.nakshatra || me?.nakshatra || "Nakshatra loading"}
              </div>
              <div className="al-rail-rows">
                <div>
                  <span>Auth</span>
                  <b>Email code</b>
                </div>
                <div>
                  <span>Streak</span>
                  <b>{pan?.streak ?? me?.streak ?? "—"} days</b>
                </div>
                <div>
                  <span>Wallet</span>
                  <b>₹{pan?.wallet ?? me?.wallet ?? "—"}</b>
                </div>
              </div>
              <p className="al-body" style={{ marginTop: 12, fontSize: 12 }}>
                <Shield size={12} style={{ verticalAlign: "middle", marginRight: 6 }} />
                Session cookie stays on this browser until you log out.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function MelapakJoin() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [signedIn, setSignedIn] = useState(false);
  const [cities, setCities] = useState<City[]>([]);
  const [meta, setMeta] = useState<{ host_name: string; mode_meta: { label: string }; complete: boolean; result: MatchResult | null } | null>(null);
  const [form, setForm] = useState<BirthForm>({ name: "", dob: "2003-08-14", tob: "09:42", place: "Pune" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<MatchResult | null>(null);

  useEffect(() => {
    api.cities().then(setCities).catch(() => undefined);
    api.me().then(() => setSignedIn(true)).catch(() => setSignedIn(false));
    if (token) {
      api
        .getMatch(token)
        .then((m) => {
          setMeta(m);
          if (m.result) setResult(m.result);
        })
        .catch(() => setErr("This link is invalid or expired."));
    }
  }, [token]);

  const join = async () => {
    if (!token) return;
    if (!signedIn && !form.name.trim()) {
      setErr("Enter your name to unlock the match.");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      const res = await api.joinMatch(token, signedIn ? {} : form);
      setResult(res.result);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not match");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="al">
      <div className="al-stage">
        <div className="al-phone">
          <div className="al-scroll">
            <button className="al-icobtn" aria-label="Back" onClick={() => navigate("/")}>
              <ChevronLeft size={16} />
            </button>
            <div className="al-eyebrow" style={{ marginTop: 18 }}>PRIVATE MELAPAK</div>
            <h2 className="al-h2" style={{ marginTop: 8 }}>
              {meta ? `${meta.host_name} invited you` : "Opening link…"}
            </h2>
            <p className="al-body" style={{ margin: "8px 0 20px" }}>
              {meta?.mode_meta.label}. 1-on-1, never public.
            </p>
            {result ? (
              <>
                <MelapakTab match={result} hostName={meta?.host_name ?? ""} copied={false} onShare={() => undefined} />
                <button className="al-pill" style={{ marginTop: 20 }} onClick={() => navigate("/")}>
                  Open my panchang
                </button>
              </>
            ) : (
              <>
                {signedIn ? (
                  <p className="al-body">Use the kundali on this account to compute Ashtakoot.</p>
                ) : (
                  <BirthFields value={form} onChange={setForm} cities={cities} />
                )}
                {err && <p className="al-err">{err}</p>}
                <button className="al-pill" style={{ marginTop: 20 }} onClick={() => void join()} disabled={busy || !meta}>
                  {busy ? "Matching nakshatras…" : signedIn ? "Match with my kundali" : "Reveal Ashtakoot score"}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Gate() {
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    onUnauthorized(() => setAuthed(false));
    api
      .me()
      .then(() => setAuthed(true))
      .catch(() => setAuthed(false));
    return () => onUnauthorized(null);
  }, []);

  if (authed === null) {
    return (
      <div className="al">
        <div className="al-stage">
          <p className="al-body al-auth-wait">Opening your sky…</p>
        </div>
      </div>
    );
  }
  if (!authed) return <Navigate to="/login" replace />;
  return <HomeApp onLogout={() => setAuthed(false)} />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthScreen />} />
      <Route path="/melapak/:token" element={<MelapakJoin />} />
      <Route path="/*" element={<Gate />} />
    </Routes>
  );
}
