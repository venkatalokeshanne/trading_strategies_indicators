// lint: helpers-library — not a conversion; the lint skips the describe_indicator and header checks.
// ─────────────────────────────────────────────────────────────────────────────
// Pine-semantics helpers for TrendSpider scripts.
//
// TrendSpider has no imports, so COPY the helpers you need into the converted
// script, below the inputs. Every helper here:
//   - works on arrays of any length (chart data or request.history data),
//   - treats null / undefined / NaN as Pine's `na`,
//   - avoids `new` and every reserved built-in name (reference/07).
// Each one states the Pine function it reproduces.
// ─────────────────────────────────────────────────────────────────────────────

// Pine na(), nz()
const isNa = v => v === null || v === undefined || Number.isNaN(v);
const nz = (v, r) => (isNa(v) ? (r === undefined ? 0 : r) : v);

// A scalar operand (e.g. the 70 in ta.crossover(rsi, 70)) as a series shaped like `like`.
const asSeries = (x, like) => (Array.isArray(x) ? x : like.map(() => x));

// Pine ta.crossover(a, b): a > b now AND a <= b on the previous bar.
const crossOver = (a, b) => {
    const bs = asSeries(b, a);
    return a.map((v, i) => i > 0
        && !isNa(v) && !isNa(bs[i]) && !isNa(a[i - 1]) && !isNa(bs[i - 1])
        && v > bs[i] && a[i - 1] <= bs[i - 1]);
};

// Pine ta.crossunder(a, b): a < b now AND a >= b on the previous bar.
const crossUnder = (a, b) => {
    const bs = asSeries(b, a);
    return a.map((v, i) => i > 0
        && !isNa(v) && !isNa(bs[i]) && !isNa(a[i - 1]) && !isNa(bs[i - 1])
        && v < bs[i] && a[i - 1] >= bs[i - 1]);
};

// Pine ta.cross(a, b): either direction.
const crossAny = (a, b) => {
    const up = crossOver(a, b), dn = crossUnder(a, b);
    return up.map((u, i) => u || dn[i]);
};

// Pine ta.change(x, n): x - x[n]. For a boolean series, true when the value changed.
const changeOf = (x, n) => {
    const k = n === undefined ? 1 : n;
    return x.map((v, i) => {
        if (i < k || isNa(v) || isNa(x[i - k])) return null;
        return typeof v === 'boolean' ? v !== x[i - k] : v - x[i - k];
    });
};

// Pine ta.barssince(cond): bars since cond was last true; na until it first is.
const barsSince = cond => {
    let last = null;
    return cond.map((c, i) => {
        if (c) last = i;
        return last === null ? null : i - last;
    });
};

// Pine ta.valuewhen(cond, src, occurrence): src at the occurrence-th most recent true cond.
const valueWhen = (cond, src, occurrence) => {
    const k = occurrence === undefined ? 0 : occurrence;
    const hits = [];
    return cond.map((c, i) => {
        if (c) hits.push(src[i]);
        return hits.length > k ? hits[hits.length - 1 - k] : null;
    });
};

// Pine ta.cum(x): running total, na treated as 0.
const cumulative = x => {
    let acc = 0;
    return x.map(v => (acc += nz(v)));
};

// Pine fixnan(x): carry the last non-na value forward.
const fixNa = x => {
    let last = null;
    return x.map(v => (isNa(v) ? last : (last = v)));
};

// Pine ta.tr(handle_na): true range. First bar is na, or high-low when handleNa is true.
// h, l, c default to the chart's own series; pass request.history arrays for other data.
const trueRange = (handleNa, h, l, c) => {
    const H = h || high, L = l || low, C = c || close;
    return H.map((hi, i) => {
        if (i === 0) return handleNa ? hi - L[0] : null;
        return Math.max(hi - L[i], Math.abs(hi - C[i - 1]), Math.abs(L[i] - C[i - 1]));
    });
};

// Pine ta.rma(x, n): Wilder's average, SMA-seeded over the first n valid values.
// Use instead of wildma() when early-bar parity with Pine matters (reference/02 §Seeding).
const rmaPine = (src, n) => {
    let acc = null, seen = 0, seed = 0;
    return src.map(v => {
        if (isNa(v)) return acc;
        if (acc === null) {
            seed += v; seen++;
            if (seen === n) acc = seed / n;
            return acc;
        }
        acc = (acc * (n - 1) + v) / n;
        return acc;
    });
};

// Pine ta.atr(n), exact: RMA (SMA-seeded) of true range.
const atrPine = (n, h, l, c) => rmaPine(trueRange(true, h, l, c), n);

// Pine ta.pivothigh(src, left, right): the pivot's value, reported on the CONFIRMATION
// bar (right bars later) — never on the pivot bar itself, which would look ahead.
// Tie-break: strictly higher than the left bars, >= the right bars. [VERIFY vs Pine]
const pivotHigh = (src, left, right) => src.map((_, i) => {
    const p = i - right;
    if (p - left < 0 || isNa(src[p])) return null;
    for (let k = p - left; k < p; k++) if (isNa(src[k]) || !(src[p] > src[k])) return null;
    for (let k = p + 1; k <= i; k++) if (isNa(src[k]) || !(src[p] >= src[k])) return null;
    return src[p];
});

const pivotLow = (src, left, right) => src.map((_, i) => {
    const p = i - right;
    if (p - left < 0 || isNa(src[p])) return null;
    for (let k = p - left; k < p; k++) if (isNa(src[k]) || !(src[p] < src[k])) return null;
    for (let k = p + 1; k <= i; k++) if (isNa(src[k]) || !(src[p] <= src[k])) return null;
    return src[p];
});

// Pine dayofweek (1 = Sunday … 7 = Saturday) from TrendSpider's (1 = Monday … 7 = Sunday).
const pineDayOfWeek = ts => (time_of(ts).dayOfWeek % 7) + 1;

// Pine month (1–12) from TrendSpider's (0–11).
const pineMonth = ts => time_of(ts).month + 1;

// Pine session string "HHMM-HHMM[:days]" → (i) => in session. Exchange time.
// End is exclusive. Handles overnight sessions. Day digits use Pine numbering.
const sessionFilter = (spec, times) => {
    const T = times || time;
    const parts = spec.split(':');
    const ends = parts[0].split('-');
    const start = +ends[0].slice(0, 2) * 60 + +ends[0].slice(2);
    const end = +ends[1].slice(0, 2) * 60 + +ends[1].slice(2);
    const days = parts[1] ? parts[1].split('').map(Number) : null;
    return i => {
        const t = time_of(T[i]);
        const m = t.hours * 60 + t.minutes;
        const inRange = start <= end ? (m >= start && m < end) : (m >= start || m < end);
        if (!inRange) return false;
        return days === null || days.indexOf((t.dayOfWeek % 7) + 1) !== -1;
    };
};

// New calendar day in exchange time. Correct for regular sessions only — for overnight
// sessions use bar_at(ts).sessionStartsAt instead (reference/03).
const isNewDay = (i, times) => {
    const T = times || time;
    if (i === 0) return true;
    const a = time_of(T[i]), b = time_of(T[i - 1]);
    return a.dayOfYear !== b.dayOfYear || a.year !== b.year;
};

// Pine ta.vwap / ta.vwap(src): session-anchored VWAP. Pine's built-in uses hlc3.
// newSession: (i) => boolean, e.g. i => isNewDay(i).
const sessionVwap = (src, newSession) => {
    let pv = 0, vv = 0;
    return src.map((v, i) => {
        if (i === 0 || newSession(i)) { pv = 0; vv = 0; }
        if (!isNa(v) && !isNa(volume[i])) { pv += v * volume[i]; vv += volume[i]; }
        return vv > 0 ? pv / vv : null;
    });
};

// Seconds per bar of the chart. [VERIFY "W" and "M" against current.resolution]
const resolutionSeconds = () => {
    const r = String(current.resolution);
    if (r === 'D') return 86400;
    if (r === 'W') return 7 * 86400;
    if (r === 'M') return 30 * 86400;            // approximate — months vary
    const n = parseInt(r, 10);
    return Number.isNaN(n) ? null : n * 60;
};

// Pine color.new(hex, transp): transp 0 = opaque … 100 = invisible.
const colorNew = (hex, transp) => {
    const h = hex.replace('#', '');
    const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${1 - (transp === undefined ? 0 : transp) / 100})`;
};
