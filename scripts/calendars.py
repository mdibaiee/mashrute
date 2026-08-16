"""Calendar conversion: Gregorian <-> Solar Hijri (Jalali) <-> Lunar Hijri (Qamari).

No third-party dependencies.

Solar Hijri
-----------
The Iranian calendar is astronomical, not arithmetic: the year begins on the day
(Tehran local time) whose *true noon* is preceded by the March equinox. The common
Birashk 33-year arithmetic approximation is wrong by one day for several years in
our period (e.g. 1285 AP), so we instead compute the March equinox with Meeus's
algorithm (Astronomical Algorithms, ch. 27) and build an exact Nowruz table for
1200-1400 AP. Validated against the ~200 dual-dated entries in the book's own
chronology -- see scripts/validate_calendars.py.

Lunar Hijri
-----------
Tabular (arithmetic) Islamic calendar. Historical Qamari dates in Iran were
observational, so computed values can differ by +/-1-2 days. Lunar dates printed
in the book are always stored verbatim and preferred; computed ones are flagged.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------- Julian Day


def gregorian_to_jd(gy: int, gm: int, gd: int) -> int:
    """Julian Day Number for a Gregorian calendar date (proleptic)."""
    a = (14 - gm) // 12
    y = gy + 4800 - a
    m = gm + 12 * a - 3
    return gd + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def jd_to_gregorian(jd: int) -> tuple[int, int, int]:
    a = jd + 32044
    b = (4 * a + 3) // 146097
    c = a - 146097 * b // 4
    d = (4 * c + 3) // 1461
    e = c - 1461 * d // 4
    m = (5 * e + 2) // 153
    day = e - (153 * m + 2) // 5 + 1
    month = m + 3 - 12 * (m // 10)
    year = 100 * b + d - 4800 + m // 10
    return year, month, day


# ------------------------------------------------- March equinox (Meeus ch.27)

_EQ_TERMS = [
    (485, 324.96, 1934.136), (203, 337.23, 32964.467), (199, 342.08, 20.186),
    (182, 27.85, 445267.112), (156, 73.14, 45036.886), (136, 171.52, 22518.443),
    (77, 222.54, 65928.934), (74, 296.72, 3034.906), (70, 243.58, 9037.513),
    (58, 119.81, 33718.147), (52, 297.17, 150.678), (50, 21.02, 2281.226),
    (45, 247.54, 29929.562), (44, 325.15, 31555.956), (29, 60.93, 4443.417),
    (18, 155.12, 67555.328), (17, 288.79, 4562.452), (16, 198.04, 62894.029),
    (14, 199.76, 31436.921), (12, 95.39, 14577.848), (12, 287.11, 31931.756),
    (12, 320.81, 34777.259), (9, 227.73, 1222.114), (8, 15.45, 16859.074),
]


def march_equinox_jde(year: int) -> float:
    """Julian Ephemeris Day of the March equinox for `year` (1000-3000 CE)."""
    y = (year - 2000) / 1000.0
    jde0 = (2451623.80984 + 365242.37404 * y + 0.05169 * y * y
            - 0.00411 * y ** 3 - 0.00057 * y ** 4)
    t = (jde0 - 2451545.0) / 36525.0
    w = math.radians(35999.373 * t - 2.47)
    dl = 1 + 0.0334 * math.cos(w) + 0.0007 * math.cos(2 * w)
    s = sum(a * math.cos(math.radians(b + c * t)) for a, b, c in _EQ_TERMS)
    return jde0 + (0.00001 * s) / dl


def _delta_t_seconds(year: int) -> float:
    """TT - UT in seconds. Espenak & Meeus polynomials; our range is 1800-2050."""
    if 1800 <= year < 1860:
        t = (year - 1800) / 1.0
        return (13.72 - 0.332447 * t + 0.0068612 * t ** 2 + 0.0041116 * t ** 3
                - 0.00037436 * t ** 4 + 0.0000121272 * t ** 5
                - 0.0000001699 * t ** 6 + 0.000000000875 * t ** 7)
    if 1860 <= year < 1900:
        t = year - 1860
        return (7.62 + 0.5737 * t - 0.251754 * t ** 2 + 0.01680668 * t ** 3
                - 0.0004473624 * t ** 4 + t ** 5 / 233174)
    if 1900 <= year < 1920:
        t = year - 1900
        return (-2.79 + 1.494119 * t - 0.0598939 * t ** 2 + 0.0061966 * t ** 3
                - 0.000197 * t ** 4)
    if 1920 <= year < 1941:
        t = year - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t ** 2 + 0.0020936 * t ** 3
    if 1941 <= year < 1961:
        t = year - 1950
        return 29.07 + 0.407 * t - t ** 2 / 233 + t ** 3 / 2547
    if 1961 <= year < 1986:
        t = year - 1975
        return 45.45 + 1.067 * t - t ** 2 / 260 - t ** 3 / 718
    if 1986 <= year < 2005:
        t = year - 2000
        return (63.86 + 0.3345 * t - 0.060374 * t ** 2 + 0.0017275 * t ** 3
                + 0.000651814 * t ** 4 + 0.00002373599 * t ** 5)
    # crude fallback outside the range we care about
    u = (year - 1820) / 100.0
    return -20 + 32 * u * u


# Tehran's local mean time offset before Iran adopted a standard zone
# (Tehran 51°25'E -> 51.4167/15 h = 3h25m40s). Iran Standard Time (+3:30)
# was adopted in 1946; our period is entirely before that.
_TEHRAN_LMT_HOURS = 51.4167 / 15.0


def nowruz_jd(jy: int) -> int:
    """JDN of 1 Farvardin of Jalali year `jy`.

    Rule: Nowruz is the day whose true noon (Tehran local apparent time,
    approximated by local mean time) follows the instant of the March equinox.
    """
    gy = jy + 621
    jde = march_equinox_jde(gy)                       # in Terrestrial Time
    jd_ut = jde - _delta_t_seconds(gy) / 86400.0      # to Universal Time
    jd_local = jd_ut + _TEHRAN_LMT_HOURS / 24.0       # to Tehran local time
    # JD n.5 == local midnight starting the civil day n+1 ... work in "day number
    # whose noon is JD integer": the civil day containing local instant jd_local
    # begins at floor(jd_local + 0.5) - 0.5.
    day_start = math.floor(jd_local + 0.5)            # JDN of that civil day
    noon_of_that_day = day_start                      # JDN integer == that day's noon
    if jd_local <= noon_of_that_day:
        return day_start
    return day_start + 1


_NOWRUZ: dict[int, int] = {}


def _nowruz(jy: int) -> int:
    if jy not in _NOWRUZ:
        _NOWRUZ[jy] = nowruz_jd(jy)
    return _NOWRUZ[jy]


def jalali_year_length(jy: int) -> int:
    return _nowruz(jy + 1) - _nowruz(jy)


def jalali_is_leap(jy: int) -> bool:
    return jalali_year_length(jy) == 366


_MONTH_LENGTHS = [31] * 6 + [30] * 5   # months 1-11; month 12 is 29 or 30


def jalali_month_length(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if jalali_is_leap(jy) else 29


def jalali_to_jd(jy: int, jm: int, jd: int) -> int:
    if not 1 <= jm <= 12:
        raise ValueError(f"bad Jalali month {jm}")
    offset = sum(_MONTH_LENGTHS[i] for i in range(jm - 1)) if jm > 1 else 0
    return _nowruz(jy) + offset + (jd - 1)


def jd_to_jalali(jd: int) -> tuple[int, int, int]:
    jy = jd_to_gregorian(jd)[0] - 621
    if jd < _nowruz(jy):
        jy -= 1
    elif jd >= _nowruz(jy + 1):
        jy += 1
    doy = jd - _nowruz(jy)          # 0-based day of year
    if doy < 186:
        return jy, doy // 31 + 1, doy % 31 + 1
    doy -= 186
    return jy, 7 + doy // 30, doy % 30 + 1


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    return jd_to_jalali(gregorian_to_jd(gy, gm, gd))


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    return jd_to_gregorian(jalali_to_jd(jy, jm, jd))


# -------------------------------------------------- Lunar Hijri (approximate)

_ISLAMIC_EPOCH = 1948440  # 16 July 622 CE, tabular/civil variant


def islamic_to_jd(iy: int, im: int, idd: int) -> int:
    return (idd + 29 * (im - 1) + (6 * im - 6) // 11
            + (iy - 1) * 354 + (3 + 11 * iy) // 30 + _ISLAMIC_EPOCH - 1)


def jd_to_islamic(jd: int) -> tuple[int, int, int]:
    jd = int(jd)
    iy = (30 * (jd - _ISLAMIC_EPOCH) + 10646) // 10631
    im = 1
    while im < 12 and jd >= islamic_to_jd(iy, im + 1, 1):
        im += 1
    idd = jd - islamic_to_jd(iy, im, 1) + 1
    return iy, im, idd


def gregorian_to_islamic(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    return jd_to_islamic(gregorian_to_jd(gy, gm, gd))


def islamic_to_gregorian(iy: int, im: int, idd: int) -> tuple[int, int, int]:
    return jd_to_gregorian(islamic_to_jd(iy, im, idd))


# ------------------------------------------------------------- Month name maps

JALALI_MONTHS_FA = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
JALALI_MONTHS_EN = ["Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
                    "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand"]
HIJRI_MONTHS_FA = ["محرم", "صفر", "ربیع‌الاول", "ربیع‌الثانی", "جمادی‌الاول",
                   "جمادی‌الثانی", "رجب", "شعبان", "رمضان", "شوال", "ذیقعده", "ذیحجه"]
HIJRI_MONTHS_EN = ["Muharram", "Safar", "Rabi‘ al-Awwal", "Rabi‘ al-Thani",
                   "Jumada al-Ula", "Jumada al-Thaniya", "Rajab", "Sha‘ban",
                   "Ramadan", "Shawwal", "Dhu al-Qa‘dah", "Dhu al-Hijjah"]
GREGORIAN_MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July",
                       "August", "September", "October", "November", "December"]
GREGORIAN_MONTHS_FA = ["ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن", "ژوئیه",
                       "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]

# Persian renderings of Gregorian months as they appear in the translation,
# including frequent OCR corruptions.
FA_GREGORIAN_MONTH_ALIASES = {
    "ژانویه": 1, "ژانویة": 1, "ژانویهٌ": 1, "ژانویۀ": 1, "انویة": 1, "ژانوية": 1,
    "ژانويه": 1, "ژانويةٌ": 1, "انویه": 1,
    "فوریه": 2, "فوریة": 2, "فوريه": 2, "فوريةٌ": 2, "فوریهٌ": 2, "فوريّة": 2, "فوريةٍ": 2,
    "فوريّه": 2, "نوریه": 2,
    "مارس": 3, "مارص": 3,
    "آوریل": 4, "اوریل": 4, "آوريل": 4, "آوربل": 4, "اوربل": 4,
    "مه": 5, "می": 5, "مي": 5,
    "ژوئن": 6, "ژرئن": 6, "ژوین": 6, "ژوثن": 6, "ژوين": 6,
    "ژوئیه": 7, "ژوئية": 7, "ژوئيةٌ": 7, "ژولیه": 7, "ژولن": 7, "ژوییه": 7,
    "ژوئیةٌ": 7, "ژوئیه‌": 7, "ژوئيه": 7, "ژوثیه": 7,
    "اوت": 8, "آگوست": 8, "اوث": 8, "اؤت": 8,
    "سپتامبر": 9, "سيتامبر": 9, "سپتامير": 9,
    "اکتبر": 10, "أکتبر": 10, "اكتبر": 10, "اکتير": 10,
    "نوامبر": 11, "نوامير": 11, "نوامبير": 11,
    "دسامبر": 12, "دسايبر": 12, "دسامير": 12,
}

FA_JALALI_MONTH_ALIASES = {
    "فروردین": 1, "نروردین": 1, "فروردين": 1, "فرودین": 1, "نروردين": 1,
    "اردیبهشت": 2, "ارديبهشت": 2, "اردببهشت": 2, "اردیبهشست": 2,
    "خرداد": 3, "خردا": 3, "خرذاد": 3,
    "تیر": 4, "تبر": 4, "تير": 4, "نیر": 4,
    "مرداد": 5, "امرداد": 5, "مرذاد": 5,
    "شهریور": 6, "شهربور": 6, "شهريور": 6, "شهریرر": 6,
    "مهر": 7, "مهرر": 7,
    "آبان": 8, "ابان": 8, "آيان": 8,
    "آذر": 9, "اذر": 9, "آزر": 9,
    "دی": 10, "دى": 10, "دي": 10,
    "بهمن": 11, "يهمن": 11,
    "اسفند": 12, "اسنند": 12, "إسفند": 12,
}

FA_HIJRI_MONTH_ALIASES = {
    "محرم": 1, "محرّم": 1, "محرام": 1,
    "صفر": 2,
    "ربیع‌الاول": 3, "ربیع الاول": 3, "ربيع الاول": 3, "ربیع‌الأول": 3, "ربیعالاول": 3,
    "ربیع‌الثانی": 4, "ربیع الثانی": 4, "ربیع‌الاخر": 4, "ربیع الاخر": 4,
    "ربيع الثاني": 4, "ربیع‌الآخر": 4,
    "جمادی‌الاول": 5, "جمادی الاول": 5, "جمادی‌الاولی": 5, "جمادی الاولی": 5,
    "جمادى الاولى": 5, "جمادی‌الاولی": 5, "جمادیالاول": 5, "جمادی الأولی": 5,
    "جمادی‌الثانی": 6, "جمادی الثانی": 6, "جمادی‌الاخری": 6, "جمادی الاخری": 6,
    "جمادی‌الاخر": 6, "جمادی الاخر": 6, "جمادی‌الثانیه": 6, "جمادی‌الآخر": 6,
    "جمادی‌الاخرى": 6,
    "رجب": 7,
    "شعبان": 8,
    "رمضان": 9,
    "شوال": 10, "شوّال": 10,
    "ذیقعده": 11, "ذی‌قعده": 11, "ذی القعده": 11, "ذیقعدة": 11, "ذی‌القعده": 11,
    "ذیعقده": 11, "ذی‌القعدة": 11,
    "ذیحجه": 12, "ذی‌حجه": 12, "ذی الحجه": 12, "ذیحجة": 12, "ذی‌الحجه": 12,
    "ذی‌الحجة": 12,
}

EN_MONTHS = {m.lower(): i + 1 for i, m in enumerate(GREGORIAN_MONTHS_EN)}
EN_MONTHS.update({m.lower()[:3]: i + 1 for i, m in enumerate(GREGORIAN_MONTHS_EN)})
# frequent OCR corruptions in the English scan
EN_MONTHS.update({"sept": 9, "aptil": 4, "apri": 4, "januaty": 1, "janua": 1,
                  "febmary": 2, "febraury": 2, "octobet": 10, "novembet": 11,
                  "decembet": 12, "augus": 8, "matrch": 3, "matrh": 3})


# ------------------------------------------------------------ Digit utilities

_FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate(_FA_DIGITS)}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate(_AR_DIGITS)})


def fa_digits_to_en(s: str) -> str:
    return s.translate(_DIGIT_MAP)


def en_digits_to_fa(s: str) -> str:
    return "".join(_FA_DIGITS[int(c)] if c.isdigit() else c for c in s)


# ------------------------------------------------------------ Formatting help

def format_jalali_fa(jy: int, jm: int, jd: int | None = None) -> str:
    body = f"{JALALI_MONTHS_FA[jm - 1]} {jy}" if jd is None else \
           f"{jd} {JALALI_MONTHS_FA[jm - 1]} {jy}"
    return en_digits_to_fa(body)


def format_jalali_en(jy: int, jm: int, jd: int | None = None) -> str:
    return f"{JALALI_MONTHS_EN[jm - 1]} {jy}" if jd is None else \
           f"{jd} {JALALI_MONTHS_EN[jm - 1]} {jy}"


def format_hijri_fa(hy: int, hm: int, hd: int | None = None) -> str:
    body = f"{HIJRI_MONTHS_FA[hm - 1]} {hy}" if hd is None else \
           f"{hd} {HIJRI_MONTHS_FA[hm - 1]} {hy}"
    return en_digits_to_fa(body)


def format_hijri_en(hy: int, hm: int, hd: int | None = None) -> str:
    return f"{HIJRI_MONTHS_EN[hm - 1]} {hy}" if hd is None else \
           f"{hd} {HIJRI_MONTHS_EN[hm - 1]} {hy}"


def format_gregorian_fa(gy: int, gm: int, gd: int | None = None) -> str:
    body = f"{GREGORIAN_MONTHS_FA[gm - 1]} {gy}" if gd is None else \
           f"{gd} {GREGORIAN_MONTHS_FA[gm - 1]} {gy}"
    return en_digits_to_fa(body)


def format_gregorian_en(gy: int, gm: int, gd: int | None = None) -> str:
    return f"{GREGORIAN_MONTHS_EN[gm - 1]} {gy}" if gd is None else \
           f"{GREGORIAN_MONTHS_EN[gm - 1]} {gd}, {gy}"


if __name__ == "__main__":
    checks = [
        ((1906, 8, 5), (1285, 5, 14)),
        ((1906, 10, 7), (1285, 7, 15)),
        ((1905, 12, 13), (1284, 9, 22)),
        ((1907, 1, 8), (1285, 10, 18)),
        ((1908, 6, 23), (1287, 4, 2)),
        ((1906, 8, 9), (1285, 5, 18)),
        ((1907, 1, 19), (1285, 10, 29)),
        ((1911, 12, 24), (1290, 10, 3)),
    ]
    bad = 0
    for g, j in checks:
        got = gregorian_to_jalali(*g)
        if got != j:
            bad += 1
            print(f"FAIL {g} -> {got}, book says {j}")
        else:
            print(f"ok   {g} -> {got}")
        assert jalali_to_gregorian(*got) == g, "round trip failed"
    print(f"\nNowruz dates: " + ", ".join(
        f"{y}AP={jd_to_gregorian(nowruz_jd(y))[1]}/{jd_to_gregorian(nowruz_jd(y))[2]}"
        for y in range(1283, 1292)))
    print("lunar 1906-08-05 ~", gregorian_to_islamic(1906, 8, 5), "(book: 14 Jumada II 1324)")
    print("lunar 1908-06-23 ~", gregorian_to_islamic(1908, 6, 23), "(book: 23 Jumada I 1326)")
    print("ALL OK" if bad == 0 else f"{bad} MISMATCHES")
