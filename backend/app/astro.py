"""Sidereal Vedic engine: Sun/Moon/planets, Panchang, Lagna, Ashtakoot."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from .data import (
    FRIENDS,
    GANA,
    GANA_NAME,
    GRAHAS,
    NADI,
    NADI_NAME,
    NAKSHATRAS,
    RASHI_EN,
    RASHI_LORD,
    RASHIS,
    UPAYS,
    YONI,
    YONI_ENEMY,
)

IST = timezone(timedelta(hours=5, minutes=30))
DEG = math.pi / 180.0


def _norm(x: float) -> float:
    return x % 360.0


def to_jd(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    utc = dt.astimezone(timezone.utc)
    y, m = utc.year, utc.month
    d = utc.day + (utc.hour + utc.minute / 60.0 + utc.second / 3600.0) / 24.0
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def lahiri_ayanamsha(jd: float) -> float:
    years = (jd - 2415020.0) / 365.256363004
    return 22.460148 + (50.2388475 / 3600.0) * years


def sun_lon(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    l0 = _norm(280.46646 + 36000.76983 * t + 0.0003032 * t * t)
    m = _norm(357.52911 + 35999.05029 * t - 0.0001537 * t * t) * DEG
    c = (
        (1.914602 - 0.004817 * t - 0.000014 * t * t) * math.sin(m)
        + (0.019993 - 0.000101 * t) * math.sin(2 * m)
        + 0.000289 * math.sin(3 * m)
    )
    return _norm(l0 + c)


def moon_lon(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    lp = _norm(218.3164477 + 481267.88123421 * t - 0.0015786 * t * t)
    d = _norm(297.8501921 + 445267.1114034 * t - 0.0018819 * t * t) * DEG
    m = _norm(357.5291092 + 35999.0502909 * t - 0.0001536 * t * t) * DEG
    mp = _norm(134.9633964 + 477198.867398 * t + 0.0086972 * t * t) * DEG
    f = _norm(93.2720950 + 483202.0175233 * t - 0.0036825 * t * t) * DEG
    s = math.sin
    dlon = (
        6288774 * s(mp)
        + 1274027 * s(2 * d - mp)
        + 658314 * s(2 * d)
        + 213618 * s(2 * mp)
        - 185116 * s(m)
        - 114332 * s(2 * f)
        + 58793 * s(2 * d - 2 * mp)
        + 57066 * s(2 * d - m - mp)
        + 53322 * s(2 * d + mp)
        + 45758 * s(2 * d - m)
        - 40923 * s(m - mp)
        - 34720 * s(d)
        - 30383 * s(m + mp)
        + 15327 * s(2 * d - 2 * f)
        - 12528 * s(mp + 2 * f)
        + 10980 * s(mp - 2 * f)
        + 10675 * s(4 * d - mp)
        + 10034 * s(3 * mp)
        + 8548 * s(4 * d - 2 * mp)
        - 7888 * s(2 * d + m - mp)
        - 6766 * s(d + m)
        - 5163 * s(d + mp)
        + 4987 * s(2 * d - m + mp)
        + 4036 * s(2 * d + m - mp)
    )
    return _norm(lp + dlon / 1_000_000.0)


def _kepler_lon(jd: float, n: float, l0: float, peri: float, e: float) -> float:
    d = jd - 2451545.0
    L = _norm(l0 + n * d)
    M = (_norm(L - peri)) * DEG
    c = (2 * e - e**3 / 4) * math.sin(M) + 1.25 * e * e * math.sin(2 * M) + (
        13 / 12
    ) * e**3 * math.sin(3 * M)
    return _norm(L + math.degrees(c))


def rahu_lon(jd: float) -> float:
    d = jd - 2451545.0
    return _norm(125.04452 - 0.0529537648 * d)


def tropical_planets(jd: float) -> dict[str, float]:
    rahu = rahu_lon(jd)
    return {
        "Sun": sun_lon(jd),
        "Moon": moon_lon(jd),
        "Mars": _kepler_lon(jd, 0.5240207766, 355.433, 336.060, 0.0934),
        "Mercury": _kepler_lon(jd, 4.092334436, 252.251, 77.456, 0.2056),
        "Jupiter": _kepler_lon(jd, 0.083085, 34.351, 14.331, 0.0489),
        "Venus": _kepler_lon(jd, 1.602130, 181.979, 131.564, 0.0068),
        "Saturn": _kepler_lon(jd, 0.033444, 50.077, 93.057, 0.0555),
        "Rahu": rahu,
        "Ketu": _norm(rahu + 180.0),
    }


def obliquity(jd: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    return 23.439291 - 0.0130042 * t


def lst_deg(jd: float, lon_east: float) -> float:
    t = (jd - 2451545.0) / 36525.0
    gmst = _norm(
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t
    )
    return _norm(gmst + lon_east)


def tropical_ascendant(jd: float, lat: float, lon: float) -> float:
    ramc = lst_deg(jd, lon) * DEG
    phi = lat * DEG
    eps = obliquity(jd) * DEG
    y = math.cos(ramc)
    x = -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps))
    return _norm(math.degrees(math.atan2(y, x)))


def rashi_index(sidereal_lon: float) -> int:
    return int(sidereal_lon // 30) % 12


def nakshatra_of(sidereal_lon: float) -> tuple[int, str, int, float]:
    span = 360.0 / 27.0
    idx = int(sidereal_lon / span) % 27
    pada = int((sidereal_lon % span) / (span / 4)) + 1
    rem = span - (sidereal_lon % span)
    return idx, NAKSHATRAS[idx], pada, rem


def fmt_dms(deg: float) -> str:
    d = int(deg)
    m = int((deg - d) * 60)
    return f"{d}°{m:02d}'"


def parse_birth(dob: str, tob: str, tz: timezone = IST) -> datetime:
    dt = datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=tz)


def natal_chart(dob: str, tob: str, lat: float, lon: float) -> dict[str, Any]:
    dt = parse_birth(dob, tob)
    jd = to_jd(dt)
    ayan = lahiri_ayanamsha(jd)
    trop = tropical_planets(jd)
    sid = {k: _norm(v - ayan) for k, v in trop.items()}
    lagna_t = tropical_ascendant(jd, lat, lon)
    lagna = _norm(lagna_t - ayan)
    lagna_r = rashi_index(lagna)
    moon_r = rashi_index(sid["Moon"])
    nidx, nname, pada, _ = nakshatra_of(sid["Moon"])

    positions = []
    for g in GRAHAS:
        lon_s = sid[g]
        r = rashi_index(lon_s)
        house = (r - lagna_r) % 12 + 1
        ni, nn, pd, _ = nakshatra_of(lon_s)
        positions.append(
            {
                "graha": g,
                "lon": round(lon_s, 4),
                "dms": fmt_dms(lon_s % 30),
                "rashi": RASHIS[r],
                "rashi_en": RASHI_EN[r],
                "house": house,
                "nakshatra": nn,
                "pada": pd,
            }
        )

    mars_house = next(p["house"] for p in positions if p["graha"] == "Mars")
    moon_house_mars = (rashi_index(sid["Mars"]) - moon_r) % 12 + 1
    mangal_lagna = mars_house in (1, 2, 4, 7, 8, 12)
    mangal_moon = moon_house_mars in (1, 2, 4, 7, 8, 12)

    return {
        "datetime_ist": dt.strftime("%Y-%m-%d %H:%M IST"),
        "jd": jd,
        "ayanamsha": round(ayan, 4),
        "lagna": RASHIS[lagna_r],
        "lagna_en": RASHI_EN[lagna_r],
        "lagna_lon": round(lagna, 4),
        "chandra_rashi": RASHIS[moon_r],
        "chandra_rashi_en": RASHI_EN[moon_r],
        "nakshatra": nname,
        "nakshatra_index": nidx,
        "pada": pada,
        "moon_lon": round(sid["Moon"], 4),
        "positions": positions,
        "mangal": {
            "from_lagna": mangal_lagna,
            "from_moon": mangal_moon,
            "status": "full"
            if mangal_lagna and mangal_moon
            else ("partial" if mangal_lagna or mangal_moon else "clear"),
        },
    }


def _sunrise_sunset(date: datetime, lat: float, lon: float) -> tuple[datetime, datetime]:
    noon = datetime(date.year, date.month, date.day, 12, 0, tzinfo=IST)
    jd = to_jd(noon)
    dec = math.asin(math.sin(obliquity(jd) * DEG) * math.sin(sun_lon(jd) * DEG))
    phi = lat * DEG
    cos_h = (math.sin(-0.83 * DEG) - math.sin(phi) * math.sin(dec)) / (
        math.cos(phi) * math.cos(dec)
    )
    cos_h = max(-1.0, min(1.0, cos_h))
    h = math.degrees(math.acos(cos_h))  # hour angle
    eot = 0.0  # small; longitude handles the bulk of civil time
    solar_noon_utc_hours = 12.0 - lon / 15.0 - eot / 60.0
    utc_date = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    noon_utc = utc_date + timedelta(hours=solar_noon_utc_hours)
    delta = timedelta(hours=h / 15.0)
    rise = (noon_utc - delta).astimezone(IST)
    sett = (noon_utc + delta).astimezone(IST)
    return rise, sett


def _fmt_hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def panchang_now(lat: float, lon: float, lagna_rashi: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(IST)
    jd = to_jd(now)
    ayan = lahiri_ayanamsha(jd)
    sun_s = _norm(sun_lon(jd) - ayan)
    moon_s = _norm(moon_lon(jd) - ayan)
    tithi_raw = _norm(moon_s - sun_s) / 12.0
    tithi_num = int(tithi_raw) + 1
    paksha = "Shukla" if tithi_num <= 15 else "Krishna"
    tithi_in_paksha = tithi_num if tithi_num <= 15 else tithi_num - 15
    nidx, nname, pada, _ = nakshatra_of(moon_s)
    yoga_idx = int(_norm(sun_s + moon_s) / (360.0 / 27.0)) % 27
    karana_idx = int(_norm(moon_s - sun_s) / 6.0) % 11

    rise, sett = _sunrise_sunset(now, lat, lon)
    day_len = (sett - rise).total_seconds()
    slot = day_len / 8.0
    # Sun=8th, Mon=2nd, Tue=7th, Wed=5th, Thu=6th, Fri=4th, Sat=3rd (1-indexed)
    vedic_wd = (now.weekday() + 1) % 7  # Sun=0
    rahu_part = {0: 8, 1: 2, 2: 7, 3: 5, 4: 6, 5: 4, 6: 3}[vedic_wd]
    rk_start = rise + timedelta(seconds=slot * (rahu_part - 1))
    rk_end = rise + timedelta(seconds=slot * rahu_part)

    noon = rise + (sett - rise) / 2
    abhijit_half = timedelta(seconds=day_len / 30.0)  # 1/15 of day → half window
    ab_start, ab_end = noon - abhijit_half, noon + abhijit_half

    in_rahu = rk_start <= now <= rk_end
    in_abhijit = ab_start <= now <= ab_end
    lagna_idx = RASHIS.index(lagna_rashi) if lagna_rashi in RASHIS else 0

    tithi_names = [
        "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
        "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
        "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima/Amavasya",
    ]
    tithi_label = tithi_names[tithi_in_paksha - 1]
    if tithi_in_paksha == 15:
        tithi_label = "Purnima" if paksha == "Shukla" else "Amavasya"

    return {
        "now": _fmt_hhmm(now),
        "date": now.strftime("%A, %d %b %Y"),
        "tithi": f"{paksha} {tithi_label}",
        "nakshatra": nname,
        "pada": pada,
        "yoga_index": yoga_idx + 1,
        "karana_index": karana_idx + 1,
        "sunrise": _fmt_hhmm(rise),
        "sunset": _fmt_hhmm(sett),
        "abhijit": {"start": _fmt_hhmm(ab_start), "end": _fmt_hhmm(ab_end), "active": in_abhijit},
        "rahu_kaal": {
            "start": _fmt_hhmm(rk_start),
            "end": _fmt_hhmm(rk_end),
            "active": in_rahu,
        },
        "lagna": lagna_rashi,
        "upay": UPAYS[lagna_idx % len(UPAYS)],
        "note": (
            "Jupiter's 5th-house transit supports contracts and long-term financial commitments today."
            if not in_rahu
            else "Rahu Kaal is active — defer major decisions and new beginnings until it lifts."
        ),
    }


def _varna_score(boy_r: int, girl_r: int) -> float:
    # 3 Brahmin, 2 Kshatriya, 1 Vaishya, 0 Shudra
    table = [2, 1, 0, 3, 2, 1, 0, 3, 2, 1, 0, 3]
    return 1.0 if table[boy_r] >= table[girl_r] else 0.0


def _vashya_score(boy_r: int, girl_r: int) -> float:
    groups = {
        0: "chatushpad", 1: "chatushpad", 2: "manava", 3: "jalachar",
        4: "vanachar", 5: "manava", 6: "manava", 7: "keeta",
        8: "chatushpad", 9: "jalachar", 10: "manava", 11: "jalachar",
    }
    if boy_r == girl_r:
        return 2.0
    if groups[boy_r] == groups[girl_r]:
        return 2.0
    friendly = {("chatushpad", "vanachar"), ("manava", "jalachar"), ("keeta", "jalachar")}
    pair = (groups[boy_r], groups[girl_r])
    if pair in friendly or (pair[1], pair[0]) in friendly:
        return 1.0
    return 0.0


def _tara_score(boy_n: int, girl_n: int) -> float:
    n = (boy_n - girl_n) % 27 + 1
    group = n % 9 or 9
    # 1 Janma, 3 Vipat, 5 Pratyak, 7 Naidhana inauspicious
    if group in (3, 5, 7):
        return 0.0
    if group == 1:
        return 1.5
    return 3.0


def _yoni_score(boy_n: int, girl_n: int) -> float:
    a, b = YONI[boy_n], YONI[girl_n]
    if a == b:
        return 4.0
    if YONI_ENEMY.get(a) == b:
        return 0.0
    return 2.0


def _graha_maitri(boy_r: int, girl_r: int) -> float:
    lb, lg = RASHI_LORD[boy_r], RASHI_LORD[girl_r]
    if lb == lg:
        return 5.0
    rel = FRIENDS[lb].get(lg, 0)
    rel2 = FRIENDS[lg].get(lb, 0)
    if rel == 1 and rel2 == 1:
        return 5.0
    if rel == 1 or rel2 == 1:
        return 4.0
    if rel == 0 and rel2 == 0:
        return 3.0
    if rel == -1 and rel2 == -1:
        return 0.0
    return 1.0


def _gana_score(boy_n: int, girl_n: int) -> float:
    gb, gg = GANA[boy_n], GANA[girl_n]
    if gb == gg:
        return 6.0
    pair = {gb, gg}
    if pair == {0, 1}:
        return 5.0
    if pair == {1, 2}:
        return 1.0
    return 0.0  # Deva–Rakshasa


def _bhakoot_score(boy_r: int, girl_r: int) -> float:
    d = min((boy_r - girl_r) % 12, (girl_r - boy_r) % 12)
    # 6/8 → d=6; 2/12 → d=2; 5/9 → d=5
    if d in (2, 5, 6):
        return 0.0
    return 7.0


def _nadi_score(boy_n: int, girl_n: int) -> float:
    return 0.0 if NADI[boy_n] == NADI[girl_n] else 8.0


def ashtakoot(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """a, b are natal_chart dicts. Girl is `a` by convention when scoring Tara from her star."""
    girl_n, boy_n = a["nakshatra_index"], b["nakshatra_index"]
    girl_r = RASHIS.index(a["chandra_rashi"])
    boy_r = RASHIS.index(b["chandra_rashi"])

    rows = [
        ("Varna", 1, _varna_score(boy_r, girl_r)),
        ("Vashya", 2, _vashya_score(boy_r, girl_r)),
        ("Tara", 3, _tara_score(boy_n, girl_n)),
        ("Yoni", 4, _yoni_score(boy_n, girl_n)),
        ("Graha Maitri", 5, _graha_maitri(boy_r, girl_r)),
        ("Gana", 6, _gana_score(boy_n, girl_n)),
        ("Bhakoot", 7, _bhakoot_score(boy_r, girl_r)),
        ("Nadi", 8, _nadi_score(boy_n, girl_n)),
    ]
    total = sum(p for _, _, p in rows)
    mangal_a = a["mangal"]["status"]
    mangal_b = b["mangal"]["status"]
    if mangal_a == "clear" and mangal_b == "clear":
        mangal = "clear"
        delta = 0
    elif mangal_a != "clear" and mangal_b != "clear":
        mangal = "cancelled"
        delta = 0
    elif mangal_a == "full" or mangal_b == "full":
        mangal = "full"
        delta = 8
    else:
        mangal = "partial"
        delta = 4

    gunas = max(0.0, total - delta)
    return {
        "gunas": round(gunas, 1),
        "max": 36,
        "delta_dosha": delta,
        "koots": [
            {
                "name": n,
                "max": m,
                "score": s,
                "ok": s >= m * 0.5,
            }
            for n, m, s in rows
        ],
        "nadi": {"score": rows[7][2], "max": 8, "kind": NADI_NAME[NADI[girl_n]]},
        "bhakoot": {"score": rows[6][2], "max": 7},
        "gana": {
            "score": rows[5][2],
            "max": 6,
            "a": GANA_NAME[GANA[girl_n]],
            "b": GANA_NAME[GANA[boy_n]],
        },
        "mangal": mangal,
        "verdict": (
            "excellent"
            if gunas >= 28
            else "good"
            if gunas >= 18
            else "workable"
            if gunas >= 12
            else "caution"
        ),
    }


def drishti_brief(chart: dict[str, Any]) -> dict[str, Any]:
    lagna = next(p for p in chart["positions"] if p["graha"] == "Sun")
    moon = next(p for p in chart["positions"] if p["graha"] == "Moon")
    jup = next(p for p in chart["positions"] if p["graha"] == "Jupiter")
    sat = next(p for p in chart["positions"] if p["graha"] == "Saturn")
    points = [
        f"Lagna {chart['lagna']} ({chart['lagna_en']}) — native presents as {chart['lagna_en']}.",
        f"Chandra in {chart['nakshatra']} pada {chart['pada']}, rashi {chart['chandra_rashi']}.",
        f"Guru in house {jup['house']} ({jup['rashi']}) — counsel on dharma and expansion from here.",
        f"Shani in house {sat['house']} ({sat['rashi']}) — delay/discipline theme; do not over-promise timelines.",
        f"Mangal dosha: {chart['mangal']['status']}.",
        f"Surya {lagna['rashi']} / Chandra {moon['rashi']} — lead with the Moon's mood, not the Sun's pride.",
    ]
    return {
        "headline": f"{chart['lagna']} Lagna · {chart['nakshatra']} Chandra",
        "points": points,
        "latency_ms": 12,
    }
