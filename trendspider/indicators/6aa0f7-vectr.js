<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('VECTR', 'lower');

// =====================================================================
// VECTR — Velocity Enhanced Composite Trend & Reversal  (TSBuild26 Version)
//
// WHAT THIS IS
// VECTR is a single ±100 trend score with four enhancement layers on top of a classic 
// RSI/DI/ADX/ATR/volume composite: price kinematics (velocity and acceleration from OLS fits), 
// a price-density structure gate, a higher-timeframe velocity check, and a two-stage exhaustion → reversal 
// state machine. A separate overlay line measures how stretched the stock is relative to its sector ETF.
//
// HOW TO READ THE PANE
//   Bars           the score. Green = bullish, red = bearish, brighter = stronger.
//   Amber bar      bullish score being discounted (up-move is decelerating).
//   Cyan bar       bearish score being discounted (down-move is decelerating).
//   Gray bar       thick structure / chop — score suppressed, no markers fire.
//   ▽ amber        bull exhaustion onset (top attempt). Hollow = weekly/HTF still up.
//   △ cyan         bear exhaustion onset (bottom attempt). Hollow = HTF still down.
//   ● red / green  reversal confirmed (down / up).
//   ◆ gray         exhaustion failed — trend resumed (a continuation signal).
//   Amber dotted   "extended": top 5% of this name's own |score| over the last year.
//   Brown dotted   "elevated": top 20%.
//   Thin white line  relative extension vs the benchmark (sector ETF), scaled so
//                  ±1σ sits on the ±33 lines and ±2σ on the ±66 lines. Turns
//                  amber above +2σ (stretched ahead of sector), cyan below −2σ.
//                  Read it as a reversion overlay: a bullish score with the
//                  white line at +66 is extended relative to its sector, not
//                  just in absolute terms.
//
// INPUTS (eight). Everything else is a constant below.
//   Enhancement Strength = 0 and Velocity Direction Weight = 0 give you the
//   original score back exactly (with whichever strength mapping you pick).
// =====================================================================

// ---------------------------------------------------------------------
// INPUTS
//   L        how many bars the "kinematics" (velocity / acceleration) look at.
//   N        how many bars everything is normalised against ("recent history").
//   enhance  one dial for all the new layers. 0 = off, 1 = full.
//   fadeThresh  how hard price has to decelerate (in units of the recent range)
//               before the fade discount reaches full strength.
//   velDirWeight  optional: let raw price velocity flip the score's SIGN
//               sooner than the slow RSI/DI inputs would. 0 = off.
//   mapping  how ADX / ATR / volume become 0..1 strengths (see below).
//   benchSel     sector ETF for the relative-extension overlay line. 'auto'
//               picks one from the ticker's industry, then its sector, then SPY.
//   relSmooth    EMA smoothing on that line (bars). 1 = raw.
// ---------------------------------------------------------------------
const L            = input.number('Kinematic Window (L)', 10, { min: 4, max: 60 });
const N            = input.number('Normalization Window (N)', 100, { min: 30, max: 500 });
const enhance      = input.number('Enhancement Strength', 1.0, { min: 0, max: 1 });
const fadeThresh   = input.number('Fade Threshold (|accel|)', 1.0, { min: 0.1, max: 5 });
const velDirWeight = input.number('Velocity Direction Weight', 0, { min: 0, max: 100 });
const mapping      = input('Strength Mapping', 'percentile', ['percentile', 'z-linear']);
const benchSel     = input.select('Benchmark', 'auto',
    ['auto', 'SPY', 'QQQ', 'RSP', 'SMH', 'SOXX', 'XSD', 'IGV', 'WCLD', 'XLK', 'XLC', 'XLF', 'KBE', 'KRE', 'KIE',
     'XLV', 'XBI', 'IHI', 'XLE', 'XOP', 'XLI', 'ITA', 'XLY', 'XRT', 'XLP', 'XLU', 'XLRE', 'XLB']);
const relSmooth    = input.number('Relative Extension Smoothing', 1, { min: 1, max: 20 });   // EMA length on the white line; 1 = none

// ---------------------------------------------------------------------
// BENCHMARK RESOLUTION
//   'auto' → match current.industry against keywords (first hit wins),
//   else current.sector, else SPY. Industry/sector strings are lower-cased
//   and stripped to letters before matching. The console prints the result.
// ---------------------------------------------------------------------
const INDUSTRY_ETF = [
    ['reit', 'XLRE'], ['realestate', 'XLRE'],
    ['semiconductorequipment', 'SMH'], ['semiconductor', 'SMH'],
    ['softwareinfrastructure', 'IGV'], ['softwareapplication', 'IGV'], ['software', 'IGV'],
    ['informationtechnologyservices', 'XLK'], ['computerhardware', 'XLK'], ['communicationequipment', 'XLK'], ['electroniccomponents', 'XLK'], ['consumerelectronics', 'XLK'],
    ['internetcontent', 'XLC'], ['interactivemedia', 'XLC'], ['entertainment', 'XLC'], ['telecom', 'XLC'], ['advertising', 'XLC'],
    ['internetretail', 'XLY'], ['banksregional', 'KRE'], ['regionalbank', 'KRE'], ['bank', 'KBE'],
    ['creditservices', 'XLF'], ['capitalmarkets', 'XLF'], ['assetmanagement', 'XLF'], ['financialdata', 'XLF'],
    ['insurance', 'KIE'], ['biotechnology', 'XBI'], ['medicaldevices', 'IHI'], ['medicalinstruments', 'IHI'],
    ['drugmanufacturers', 'XLV'], ['healthcare', 'XLV'], ['medical', 'XLV'], ['diagnostics', 'XLV'],
    ['oilgas', 'XOP'], ['oil', 'XLE'], ['energy', 'XLE'], ['uranium', 'XLE'], ['solar', 'XLE'],
    ['aerospace', 'ITA'], ['defense', 'ITA'],
    ['industrial', 'XLI'], ['machinery', 'XLI'], ['railroads', 'XLI'], ['trucking', 'XLI'], ['airlines', 'XLI'], ['engineering', 'XLI'], ['building', 'XLI'], ['electricalequipment', 'XLI'], ['staffing', 'XLI'], ['waste', 'XLI'],
    ['retail', 'XRT'], ['apparel', 'XRT'], ['footwear', 'XRT'], ['department', 'XRT'], ['luxury', 'XRT'],
    ['restaurant', 'XLY'], ['auto', 'XLY'], ['homebuild', 'XLY'], ['leisure', 'XLY'], ['lodging', 'XLY'], ['gambling', 'XLY'], ['travel', 'XLY'], ['furnishings', 'XLY'],
    ['beverages', 'XLP'], ['grocery', 'XLP'], ['packagedfoods', 'XLP'], ['household', 'XLP'], ['tobacco', 'XLP'], ['discountstores', 'XLP'], ['confectioners', 'XLP'],
    ['utilities', 'XLU'], ['utility', 'XLU'], ['electric', 'XLU'],
    ['chemical', 'XLB'], ['steel', 'XLB'], ['copper', 'XLB'], ['gold', 'XLB'], ['silver', 'XLB'], ['aluminum', 'XLB'], ['lumber', 'XLB'], ['paper', 'XLB'], ['packaging', 'XLB'], ['agricultural', 'XLB'], ['metal', 'XLB'], ['mining', 'XLB'],
];
const SECTOR_ETF = {
    technology: 'XLK', healthcare: 'XLV', finance: 'XLF', financial: 'XLF', utilities: 'XLU', energy: 'XLE',
    industrials: 'XLI', consumerdefensive: 'XLP', consumercyclical: 'XLY', consumer: 'XLY',
    communication: 'XLC', realestate: 'XLRE', materials: 'XLB', basicmaterials: 'XLB',
};
const norm = (v) => String(v ?? '').toLowerCase().replace(/[^a-z]/g, '');
const industryId = norm(current && current.industry);
const sectorId   = norm(current && current.sector);
let benchTicker = 'SPY', benchHow = 'default';
if (benchSel !== 'auto') { benchTicker = benchSel; benchHow = 'manual'; }
else {
    const hit = industryId ? INDUSTRY_ETF.find((pair) => industryId.indexOf(pair[0]) >= 0) : null;
    const sec = sectorId ? Object.keys(SECTOR_ETF).find((k) => sectorId === k || sectorId.indexOf(k) >= 0 || k.indexOf(sectorId) >= 0) : null;
    if (hit)      { benchTicker = hit[1];          benchHow = 'industry'; }
    else if (sec) { benchTicker = SECTOR_ETF[sec]; benchHow = 'sector'; }
}

// ---------------------------------------------------------------------
// CONSTANTS — deliberately NOT inputs. Change them here if you must.
// ---------------------------------------------------------------------
const RSI_LEN = 14, ADX_LEN = 14, DI_SMOOTH = 9, ATR_LEN = 14;       // standard indicator periods
const VOL_WMA = 8, VOL_EMA = 5;                                        // how volume is smoothed before ranking
const W_RSI = 0.40, W_DI = 0.60;                                       // direction blend: RSI vs DI
const W_ADX = 0.45, W_ATR = 0.30, W_VOL = 0.25;                        // conviction blend: ADX vs ATR vs volume
const ADX_FULL = 25;                                                   // z-linear mode only: ADX level where DI counts fully

const FADE_W = 0.60, STRUCT_W = 0.50, WEEKLY_W = 0.60;                 // how much each layer can cut conviction, at enhance = 1
const FADE_EXIT_RATIO = 0.25;                                          // discount fades back out at 25% of the threshold (hysteresis)
const FADE_SMOOTH = 2;                                                 // light smoothing on the deterioration value
const DENS_LOOKBACK = 3 * L, DENS_TOL_ATR = 0.30, DENS_THIN = 0.25, DENS_THICK = 0.40;   // structure: window, tolerance, thin/thick cutoffs
const HTF_L = Math.max(4, Math.round(0.6 * L)), HTF_FULL = 0.50;       // higher-TF: buckets in the fit, |velocity| that counts as fully "against"
const CONFIRM_VEL = 0.0, CONFIRM_EXTRA = 0.15;                         // reversal confirms when velocity crosses 0 (+extra if HTF against)
const PENDING_MAX = L, FAIL_BUFFER_ATR = 0.25;                         // pending window length; new extreme must beat onset by this many ATR
const EXT_LOOKBACK = 250, EXT_P_HIGH = 0.95, EXT_P_MID = 0.80;          // "extended" bands: trailing window and percentiles
const REL_Z_LEVEL = 2.0, REL_SCALE = 33;                                // relative extension: ±2σ threshold; ×33 puts ±2σ on the ±66 lines

const fadeWeight   = FADE_W   * enhance;
const structWeight = STRUCT_W * enhance;
const htfWeight    = WEEKLY_W * enhance;
const fadeExit     = fadeThresh * FADE_EXIT_RATIO;
const confirmExtra = CONFIRM_EXTRA * enhance;

// ---------------------------------------------------------------------
// HELPERS — small utilities used everywhere below
// ---------------------------------------------------------------------
const isNum = (v) => v !== null && v !== undefined && !Number.isNaN(v);
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// Run fn on the last `len` values ending at each bar. Null until there are enough bars.
const windowed = (src, len, fn) => for_every(src, (_v, _p, i) => {
    if (i < len - 1) return null;
    const w = src.slice(i - len + 1, i + 1);
    for (let j = 0; j < w.length; j++) if (!isNum(w[j])) return null;
    return fn(w);
});

// "How unusual is today vs the last N bars," in standard deviations, capped at ±3.
const zscore = (src, len) => {
    const mean = sma(src, len), sd = stdev(src, len);
    return for_every(src, mean, sd, (v, m, s) =>
        (!isNum(v) || !isNum(m) || !isNum(s) || s === 0) ? null : clamp((v - m) / s, -3, 3));
};

// "What fraction of the last N values is today above," 0..1. Robust to outliers.
const prank = (src, len) => for_every(src, (v, _p, i) => {
    if (!isNum(v) || i < len - 1) return null;
    let below = 0, ties = 0, n = 0;
    for (let j = i - len + 1; j <= i; j++) {
        const x = src[j];
        if (!isNum(x)) continue;
        n++;
        if (x < v) below++; else if (x === v) ties++;
    }
    return n > 1 ? (below + 0.5 * (ties - 1)) / (n - 1) : 0.5;
});

// Original mapping: z of -3 → 0, z of 0 → 0.5, z of +3 → 1.
const zStrength = (z) => for_every(z, (v) => (isNum(v) ? (v + 3) / 6 : null));

// The value sitting at percentile p of the trailing window (e.g. "the 95th-percentile score").
const ptile = (src, len, p, minN) => for_every(src, (_v, _p, i) => {
    const vals = [];
    for (let j = Math.max(0, i - len + 1); j <= i; j++) if (isNum(src[j])) vals.push(src[j]);
    if (vals.length < minN) return null;
    vals.sort((a, b) => a - b);
    return vals[Math.min(vals.length - 1, Math.floor(p * (vals.length - 1)))];
});

// =====================================================================
// MODULE 1 — BASE COMPOSITE
//   Direction: which way is price leaning, and how unusually so?
//     RSI (momentum) and the DI spread (+DI minus −DI, i.e. directional
//     pressure) are each turned into a z-score, then blended 40/60.
//     The DI spread is first multiplied by an ADX weight so it only counts
//     when there is actually a trend to have a direction.
//   Conviction: is there energy behind it?
//     ADX (trend organisation), ATR (volatility), volume (participation),
//     each turned into a 0..1 strength and blended 45/30/25.
//   Base score = Direction × Conviction × 33.3, clamped to ±100.
// =====================================================================
const rsiZ = zscore(rsi(close, RSI_LEN), N);

// Wilder's ADX / +DI / −DI, built by hand so the DI lines are available separately
const tr = series_of(0), pdm = series_of(0), mdm = series_of(0);
for (let i = 1; i < close.length; i++) {
    const up = high[i] - high[i - 1], dn = low[i - 1] - low[i];
    tr[i] = Math.max(high[i] - low[i], Math.abs(high[i] - close[i - 1]), Math.abs(low[i] - close[i - 1]));
    if (up > dn && up > 0) pdm[i] = up;
    if (dn > up && dn > 0) mdm[i] = dn;
}
const sTR = wildma(tr, ADX_LEN);
const plusDI  = for_every(wildma(pdm, ADX_LEN), sTR, (d, t) => (!isNum(t) || t === 0 ? 0 : 100 * d / t));
const minusDI = for_every(wildma(mdm, ADX_LEN), sTR, (d, t) => (!isNum(t) || t === 0 ? 0 : 100 * d / t));
const dx      = for_every(plusDI, minusDI, (p, m) => (p + m === 0 ? 0 : 100 * Math.abs(p - m) / (p + m)));
const adxRaw  = wildma(dx, ADX_LEN);

// Strengths (0..1). 'percentile' = where today sits in its own last-N history.
// 'z-linear' = the original z-score mapping (kept so you can A/B the two).
const adxRank = prank(adxRaw, N);
const atrRaw  = atr(ATR_LEN);
const volSm   = ema(wma(volume, VOL_WMA), VOL_EMA);

const adxStrength = mapping === 'percentile' ? adxRank : zStrength(zscore(adxRaw, N));
const atrStrength = mapping === 'percentile' ? prank(atrRaw, N)
    : zStrength(zscore(for_every(atrRaw, (v) => (isNum(v) && v > 0 ? Math.log(v) : null)), N));
const volStrength = mapping === 'percentile' ? prank(volSm, N)
    : zStrength(zscore(ema(wma(for_every(volume, sma(volume, N), stdev(volume, N), (v, m, s) => (!isNum(s) || s === 0 ? 0 : (v - m) / s)), VOL_WMA), VOL_EMA), N));

// DI spread, weighted by "is there a trend" (ADX), then z-scored
const diDelta   = ema(for_every(plusDI, minusDI, (p, m) => p - m), DI_SMOOTH);
const diWeight  = mapping === 'percentile' ? adxRank : for_every(adxRaw, (a) => (isNum(a) ? Math.min(a / ADX_FULL, 1) : null));
const diZ       = zscore(for_every(diDelta, diWeight, (d, w) => (isNum(d) && isNum(w) ? d * w : null)), N);

const direction  = for_every(rsiZ, diZ, (r, d) => (isNum(r) && isNum(d) ? r * W_RSI + d * W_DI : null));
const conviction = for_every(adxStrength, atrStrength, volStrength, (a, t, v) =>
    (isNum(a) && isNum(t) && isNum(v) ? a * W_ADX + t * W_ATR + v * W_VOL : null));

const compositeBase = for_every(direction, conviction, (d, c) => (isNum(d) && isNum(c) ? clamp(d * c * (100 / 3), -100, 100) : null));

// =====================================================================
// MODULE 2 — KINEMATICS (from SMI Kinematics)
//   Fit a straight line and a parabola to the last L closes.
//     velocity     = slope of the line  → how fast price is moving
//     acceleration = curvature of the parabola at the most recent bar
//                    → is that motion speeding up or slowing down
//   Both are divided by the high-low range of the same L bars, so they are
//   in "fractions of the recent range" and comparable across any ticker or
//   timeframe. Acceleration is the earliest thing to change when a trend
//   tires: price keeps making highs, just more slowly.
//   The fit weights depend only on L, so they are computed once up front.
// =====================================================================
const u = []; for (let i = 0; i < L; i++) u.push((i - (L - 1)) / (L - 1));   // time axis from -1 (oldest) to 0 (now)
const uMean = u.reduce((a, v) => a + v, 0) / L;
const Suu   = u.reduce((a, v) => a + (v - uMean) ** 2, 0);
const wLin  = u.map((v) => (v - uMean) / Suu);                              // weights that give the line's slope
const S = { u: 0, u2: 0, u3: 0, u4: 0 };
u.forEach((v) => { S.u += v; S.u2 += v * v; S.u3 += v ** 3; S.u4 += v ** 4; });
const M = [[L, S.u, S.u2], [S.u, S.u2, S.u3], [S.u2, S.u3, S.u4]];
const detM = M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0]) + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]);
assert(Math.abs(detM) > 1e-12, 'Quadratic design matrix is singular; increase L');
const inv2 = [ (M[1][0] * M[2][1] - M[1][1] * M[2][0]) / detM, -(M[0][0] * M[2][1] - M[0][1] * M[2][0]) / detM, (M[0][0] * M[1][1] - M[0][1] * M[1][0]) / detM ];
const wAcc = u.map((v) => inv2[0] + inv2[1] * v + inv2[2] * v * v);          // weights that give the parabola's curvature

const rangeL   = for_every(windowed(high, L, (w) => Math.max(...w)), windowed(low, L, (w) => Math.min(...w)), (h, l) => (isNum(h) && isNum(l) && h - l > 0 ? h - l : null));
const accel    = for_every(windowed(close, L, (w) => 2 * w.reduce((s, p, i) => s + wAcc[i] * p, 0)), rangeL, (q, rg) => (isNum(q) && isNum(rg) ? q / rg : null));
const velocity = for_every(windowed(close, L, (w) => w.reduce((s, p, i) => s + wLin[i] * p, 0)), rangeL, (d, rg) => (isNum(d) && isNum(rg) ? clamp(d / rg, -1, 1) : null));

// Optional: mix velocity into direction. Velocity has no memory of the old regime,
// so it lets the score's sign turn at a V-bottom while RSI/DI are still anchored to the crash.
const directionEnh = for_every(direction, velocity, (d, y) => {
    if (!isNum(d)) return null;
    if (velDirWeight === 0 || !isNum(y)) return d;
    const wv = velDirWeight / 100;
    return (1 - wv) * d + wv * (3 * y);
});

// =====================================================================
// MODULE 3 — HIGHER-TIMEFRAME VELOCITY
//   The same velocity, but measured on the next timeframe up, built from
//   this chart's own bars: days on an intraday chart, weeks on a daily,
//   months on a weekly. Each bar only ever sees the last COMPLETED bucket,
//   so nothing repaints. Used to answer: "is the bigger trend still going
//   the other way?" — a daily bottom attempt inside a falling weekly is
//   usually a pause, not a bottom.
//   If there aren't enough buckets yet, the value is 0 (neutral), never null.
// =====================================================================
const resStr = String((current && current.resolution) || 'D').toUpperCase();
const htfKind = resStr.indexOf('W') >= 0 ? 'month' : (resStr.indexOf('D') >= 0 ? 'week' : 'day');
const toSec = (ts) => (ts > 1e11 ? ts / 1000 : ts);
const bucketId = (ts) => {
    const sec = toSec(ts);
    if (htfKind === 'day')  return Math.floor((sec - 5 * 3600) / 86400);            // roughly US-session-aligned day
    if (htfKind === 'week') return Math.floor((sec / 86400 + 3) / 7);              // Monday-start week
    return monthIndex(Math.floor(sec / 86400));                                    // calendar month
};
// days-since-epoch → year*12 + month, by calendar arithmetic (TrendSpider forbids `new Date`)
function monthIndex(days) {
    const z = days + 719468;
    const era = Math.floor(z / 146097);
    const doe = z - era * 146097;
    const yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
    const doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
    const mp  = Math.floor((5 * doy + 2) / 153);
    const m   = mp < 10 ? mp + 3 : mp - 9;
    const y   = yoe + era * 400 + (m <= 2 ? 1 : 0);
    return y * 12 + (m - 1);
}
const uh = []; for (let i = 0; i < HTF_L; i++) uh.push((i - (HTF_L - 1)) / (HTF_L - 1));
const uhMean = uh.reduce((a, v) => a + v, 0) / HTF_L;
const wLinH  = uh.map((v) => (v - uhMean) / uh.reduce((a, x) => a + (x - uhMean) ** 2, 0));
const bC = [], bH = [], bLo = [];                 // close / high / low of each completed bucket
const htfVelocity = series_of(0);
let curB = null, curH = -Infinity, curL = Infinity, curC = null, lastHtfVel = 0;
for (let i = 0; i < close.length; i++) {
    const b = bucketId(time[i]);
    if (curB !== null && b !== curB) {            // a bucket just completed: store it, refit
        bC.push(curC); bH.push(curH); bLo.push(curL);
        const n = bC.length;
        if (n >= HTF_L) {
            let disp = 0, hi = -Infinity, lo = Infinity;
            for (let j = 0; j < HTF_L; j++) { const k = n - HTF_L + j; disp += wLinH[j] * bC[k]; hi = Math.max(hi, bH[k]); lo = Math.min(lo, bLo[k]); }
            lastHtfVel = hi - lo > 0 ? clamp(disp / (hi - lo), -1, 1) : 0;
        }
        curH = -Infinity; curL = Infinity;
    }
    curB = b; curH = Math.max(curH, high[i]); curL = Math.min(curL, low[i]); curC = close[i];
    htfVelocity[i] = lastHtfVel;                  // this bar sees only completed buckets
}
const htfOk = bC.length >= HTF_L;

// =====================================================================
// MODULE 4 — STRUCTURE (from PRISM)
//   "How many times has price already been here recently?"
//   For each bar, count how many of the previous 3L bars closed within
//   0.3 ATR of today's close, plus how many had a range that contains it.
//   In a trend today's close is at the edge of history → low count.
//   In a range it's in the middle of everything → high count ("thick").
//   Thick structure shrinks the score and blocks exhaustion markers,
//   because deceleration inside a tight range isn't exhaustion of anything.
// =====================================================================
const density = for_every(close, (c, _p, i) => {
    if (i < DENS_LOOKBACK || !isNum(atrRaw[i])) return null;
    const tol = atrRaw[i] * DENS_TOL_ATR;
    let n = 0;
    for (let j = 1; j <= DENS_LOOKBACK; j++) {
        if (Math.abs(close[i - j] - c) <= tol) n++;
        if (high[i - j] >= c && low[i - j] <= c) n++;
    }
    return n / DENS_LOOKBACK;
});
const structure = for_every(density, (d) => (isNum(d) ? clamp((d - DENS_THIN) / (DENS_THICK - DENS_THIN), 0, 1) : null));   // 0 thin .. 1 thick
const thick     = for_every(density, (d) => (isNum(d) && d > DENS_THICK ? 1 : 0));

// =====================================================================
// MODULE 5 — DISCOUNTS → ENHANCED SCORE
//   deterioration: how strongly acceleration is fighting the direction,
//     scaled 0..1 between the exit and entry thresholds, lightly smoothed.
//     (Up-move decelerating, or down-move decelerating.)
//   htfAgainst: how strongly the higher-TF trend opposes a reversal, 0..1.
//   Conviction is then multiplied down by:
//     (1 − fade × deterioration)  — less so when the HTF disagrees with the reversal
//     (1 − structure weight × structure)
//   and the enhanced score is Direction × that conviction × 33.3.
// =====================================================================
const deterioration = ema(for_every(accel, directionEnh, (a, d) => {
    if (!isNum(a) || !isNum(d)) return null;
    const opposing = d > 0 ? -a : (d < 0 ? a : 0);        // positive when acceleration fights the direction
    return clamp((opposing - fadeExit) / Math.max(fadeThresh - fadeExit, 1e-9), 0, 1);
}), FADE_SMOOTH);

const htfAgainst = series_of(0);                          // plain loop so it can never be null
for (let i = 0; i < close.length; i++) {
    const d = directionEnh[i], hv = htfVelocity[i];
    if (!isNum(d) || !isNum(hv) || d === 0) continue;
    htfAgainst[i] = clamp((d < 0 ? -hv : hv) / HTF_FULL, 0, 1);
}

const convictionEnh = series_of(null);
for (let i = 0; i < close.length; i++) {
    const c = conviction[i];
    if (!isNum(c)) continue;
    const det = isNum(deterioration[i]) ? deterioration[i] : 0;
    const st  = isNum(structure[i]) ? structure[i] : 0;
    const fw  = fadeWeight * (1 - htfWeight * htfAgainst[i]);
    convictionEnh[i] = c * (1 - fw * det) * (1 - structWeight * st);
}
const composite = for_every(directionEnh, convictionEnh, (d, c) => (isNum(d) && isNum(c) ? clamp(d * c * (100 / 3), -100, 100) : null));

// =====================================================================
// MODULE 6 — EXTENDED BANDS
//   Instead of fixed ±33/±66 lines, ask "how big is today's score compared
//   to this name's own last year?" p95 of |score| = extended, p80 = elevated.
//   Trailing window only, so the lines never use future bars.
// =====================================================================
const absScore = for_every(composite, (v) => (isNum(v) ? Math.abs(v) : null));
const extHigh  = ptile(absScore, EXT_LOOKBACK, EXT_P_HIGH, Math.min(EXT_LOOKBACK, N));
const extMid   = ptile(absScore, EXT_LOOKBACK, EXT_P_MID,  Math.min(EXT_LOOKBACK, N));
const extended = for_every(composite, extHigh, (v, e) => (isNum(v) && isNum(e) && Math.abs(v) >= e ? 1 : 0));

// =====================================================================
// MODULE 6b — RELATIVE EXTENSION vs BENCHMARK (overlay line)
//   "Is this stock stretched ahead of / behind its sector by more than it
//   usually is?" — the one thing the composite can't see, because every
//   other input is the stock alone. Ratio = log(stock / benchmark), then
//   z-scored against its own last N bars. Also computes the OLS slope of
//   the ratio (is the gap widening or closing) for the signals only.
//   Benchmark bars are matched to chart bars by timestamp; if the request
//   fails the line is simply blank — nothing else is affected.
// =====================================================================
let benchClose = series_of(null);
let benchOk = false;
try {
    const b = await request.history(benchTicker, current.resolution);
    if (b && !b.error && b.close && b.time) {
        // as-of alignment: each chart bar takes the latest benchmark bar at or before its timestamp.
        // Exact matches for regular-session bars; extended-hours bars carry the last regular close forward.
        const idx = []; for (let i = 0; i < b.time.length; i++) idx.push(i);
        idx.sort((p, q) => b.time[p] - b.time[q]);
        let k = 0, hits = 0, lastV = null;
        for (let i = 0; i < time.length; i++) {
            while (k < idx.length && b.time[idx[k]] <= time[i]) { const v = b.close[idx[k]]; if (isNum(v)) lastV = v; k++; }
            if (lastV !== null) { benchClose[i] = lastV; hits++; }
        }
        benchOk = hits > N;
    }
} catch (e) { benchOk = false; }

const relRatio = series_of(null);
for (let i = 0; i < close.length; i++) {
    const bc = benchClose[i];
    if (isNum(bc) && bc > 0 && close[i] > 0) relRatio[i] = Math.log(close[i] / bc);
}
const relExtRaw = series_of(null);                  // z-score of the ratio vs its own trailing N bars
for (let i = N - 1; i < close.length; i++) {
    if (!isNum(relRatio[i])) continue;
    let sm = 0, s2 = 0, n = 0;
    for (let j = i - N + 1; j <= i; j++) { const v = relRatio[j]; if (isNum(v)) { sm += v; s2 += v * v; n++; } }
    if (n < N * 0.8) continue;
    const mean = sm / n, sd = Math.sqrt(Math.max(s2 / n - mean * mean, 0));
    relExtRaw[i] = sd > 1e-12 ? clamp((relRatio[i] - mean) / sd, -4, 4) : 0;
}
// optional smoothing (plain EMA loop so leading nulls don't poison it); 1 = raw
const relExt = series_of(null);
{
    const k = 2 / (relSmooth + 1);
    let e = null;
    for (let i = 0; i < close.length; i++) {
        const v = relExtRaw[i];
        if (!isNum(v)) continue;
        e = (e === null || relSmooth <= 1) ? v : v * k + e * (1 - k);
        relExt[i] = e;
    }
}
const relVel = series_of(null);                     // OLS slope of the ratio over L bars (signals only)
for (let i = L - 1; i < close.length; i++) {
    let disp = 0, ok = true;
    for (let j = 0; j < L; j++) { const v = relRatio[i - L + 1 + j]; if (!isNum(v)) { ok = false; break; } disp += wLin[j] * v; }
    if (ok) relVel[i] = disp;
}
const relHigh    = for_every(relExt, (e) => (isNum(e) && e >=  REL_Z_LEVEL ? 1 : 0));
const relLow     = for_every(relExt, (e) => (isNum(e) && e <= -REL_Z_LEVEL ? 1 : 0));
const relOverExt = for_every(relExt, relVel, (e, v) => (isNum(e) && isNum(v) && e >=  REL_Z_LEVEL && v < 0 ? 1 : 0));   // stretched ahead, gap closing
const relCatchUp = for_every(relExt, relVel, (e, v) => (isNum(e) && isNum(v) && e <= -REL_Z_LEVEL && v > 0 ? 1 : 0));   // stretched behind, gap closing

// =====================================================================
// MODULE 7 — EXHAUSTION → TWO-STAGE REVERSAL
//   An exhaustion "onset" is the first bar the fade discount switches on
//   (deterioration ≥ 0.5), outside thick structure. That opens a PENDING
//   window of L bars, which resolves one of three ways:
//     CONFIRMED  velocity crosses zero the other way (needs an extra margin
//                if the higher-TF trend is against the reversal)
//     FAILED     price makes a new extreme beyond the onset bar by > 0.25 ATR
//                (the trend resumed — a continuation signal in its own right)
//     EXPIRED    neither happened; the window closes quietly
//   A new onset while pending simply re-anchors the extreme.
// =====================================================================
const gateOn     = enhance > 0;
const discountOn = for_every(deterioration, thick, (v, t) => (isNum(v) && v >= 0.5 && fadeWeight > 0 && !(gateOn && t === 1) ? 1 : 0));
const onset      = (flag) => for_every(flag, (v, _p, i) => (v === 1 && i > 0 && flag[i - 1] !== 1 ? 1 : 0));
const bullExhaustOn = for_every(onset(discountOn), composite, (o, sc) => (o === 1 && isNum(sc) && sc >= 0 ? 1 : 0));   // top attempt
const bearExhaustOn = for_every(onset(discountOn), composite, (o, sc) => (o === 1 && isNum(sc) && sc <  0 ? 1 : 0));   // bottom attempt

const revUp = series_of(0), bearFail = series_of(0), revDn = series_of(0), bullFail = series_of(0);
const pendingBottom = series_of(0), pendingTop = series_of(0);
let botOpen = false, botLow = 0, botSince = 0, botAg = 0, topOpen = false, topHigh = 0, topSince = 0, topAg = 0;
for (let i = 0; i < close.length; i++) {
    const v = velocity[i], buf = FAIL_BUFFER_ATR * (atrRaw[i] || 0);
    // bottom attempt
    if (bearExhaustOn[i] === 1) { botOpen = true; botLow = low[i]; botSince = i; botAg = htfAgainst[i]; }
    else if (botOpen) {
        if (low[i] < botLow - buf)                                   { bearFail[i] = 1; botOpen = false; }
        else if (isNum(v) && v > CONFIRM_VEL + confirmExtra * botAg) { revUp[i] = 1;    botOpen = false; }
        else if (i - botSince > PENDING_MAX)                         { botOpen = false; }
    }
    // top attempt
    if (bullExhaustOn[i] === 1) { topOpen = true; topHigh = high[i]; topSince = i; topAg = htfAgainst[i]; }
    else if (topOpen) {
        if (high[i] > topHigh + buf)                                    { bullFail[i] = 1; topOpen = false; }
        else if (isNum(v) && v < -(CONFIRM_VEL + confirmExtra * topAg)) { revDn[i] = 1;    topOpen = false; }
        else if (i - topSince > PENDING_MAX)                            { topOpen = false; }
    }
    pendingBottom[i] = botOpen ? 1 : 0; pendingTop[i] = topOpen ? 1 : 0;
}

// =====================================================================
// MODULE 8 — PAINT
//   Every paint() runs on every execution with a fixed name (TrendSpider
//   drops lines whose names change or that are painted conditionally).
//   Markers are point objects with a `marker` block on an otherwise
//   transparent line — that is what draws the triangles, circles, diamonds.
// =====================================================================
const bandColor = (s) => {
    if (!isNum(s)) return '#555555';
    if (s >= 66) return '#00e676'; if (s >= 33) return '#90ee90'; if (s > 10) return 'rgba(129,199,132,0.7)';
    if (s >= -10) return '#777777'; if (s > -33) return 'rgba(239,154,154,0.7)'; if (s > -66) return '#ff7777';
    return '#f44336';
};
const colors = for_every(composite, discountOn, thick, (s, on, t) =>
    (gateOn && t === 1 ? 'rgba(160,160,160,0.55)' : on === 1 ? (s >= 0 ? '#FFB020' : '#00E5FF') : bandColor(s)));
paint(composite, { name: 'Composite Trend Score', style: 'column', color: colors });

// onset markers are hollow when the higher-TF trend is against the reversal
const mark = (flag, offset, symbol, fill, hollowWhenAgainst) => for_every(flag, (v, _p, i) => {
    if (v !== 1 || !isNum(composite[i])) return null;
    const ag = hollowWhenAgainst && (htfAgainst[i]) >= 0.5;
    return { y: composite[i] + offset, marker: { enabled: true, radius: 5, symbol, fillColor: ag ? 'rgba(0,0,0,0)' : fill, lineColor: ag ? fill : '#111111', lineWidth: ag ? 2 : 1 } };
});
paint(mark(bullExhaustOn,  8,  'triangle-down', '#FFB020', true),  { name: 'Bull Exhaustion Marker',   color: 'transparent' });
paint(mark(bearExhaustOn, -8,  'triangle',      '#00E5FF', true),  { name: 'Bear Exhaustion Marker',   color: 'transparent' });
paint(mark(revUp,        -16,  'circle',        '#00E676', false), { name: 'Reversal Up Marker',       color: 'transparent' });
paint(mark(revDn,         16,  'circle',        '#FF3D71', false), { name: 'Reversal Down Marker',     color: 'transparent' });
paint(mark(bearFail,     -16,  'diamond',       '#9E9E9E', false), { name: 'Bear Exhaust Fail Marker', color: 'transparent' });
paint(mark(bullFail,      16,  'diamond',       '#9E9E9E', false), { name: 'Bull Exhaust Fail Marker', color: 'transparent' });

// relative extension overlay: ±1σ on the ±33 lines, ±2σ on the ±66 lines
const relColor = for_every(relExt, (e) => (!isNum(e) ? '#888888' : e >= REL_Z_LEVEL ? '#FFB020' : e <= -REL_Z_LEVEL ? '#00E5FF' : 'rgba(255,255,255,0.75)'));
paint(for_every(relExt, (e) => (isNum(e) ? e * REL_SCALE : null)), { name: 'Relative Extension', color: relColor, thickness: 1, ignoreWhenScaling: true });

// hidden diagnostics — toggle on from the chart key
const x100 = (s) => for_every(s, (v) => (isNum(v) ? v * 100 : null));
paint(compositeBase,          { name: 'Composite (Base)',       color: '#B0BEC5', thickness: 1, invisibleByDefault: true });
paint(x100(deterioration),    { name: 'Deterioration x100',     color: '#FFB020', thickness: 1, invisibleByDefault: true, ignoreWhenScaling: true });
paint(for_every(accel, (v) => (isNum(v) ? v * 25 : null)), { name: 'Price Accel x25', color: '#C77DFF', thickness: 1, invisibleByDefault: true, ignoreWhenScaling: true });
paint(x100(velocity),         { name: 'Price Velocity x100',    color: '#4FC3F7', thickness: 1, invisibleByDefault: true, ignoreWhenScaling: true });
paint(x100(htfVelocity),      { name: 'HTF Velocity x100',      color: '#FFD54F', thickness: 1, invisibleByDefault: true, ignoreWhenScaling: true });
paint(x100(density),          { name: 'Structure Density x100', color: '#9E9E9E', thickness: 1, invisibleByDefault: true, ignoreWhenScaling: true });
paint(x100(conviction),       { name: 'Conviction x100',        color: '#80CBC4', thickness: 1, invisibleByDefault: true, ignoreWhenScaling: true });

// dynamic bands (this name's own distribution) and dimmed static reference lines
paint(extHigh,                                                { name: 'Extended Upper p95', color: '#FFB020', thickness: 1, style: 'dotted' });
paint(for_every(extHigh, (v) => (isNum(v) ? -v : null)),      { name: 'Extended Lower p95', color: '#FFB020', thickness: 1, style: 'dotted' });
paint(extMid,                                                 { name: 'Elevated Upper p80', color: '#8D6E63', thickness: 1, style: 'dotted' });
paint(for_every(extMid, (v) => (isNum(v) ? -v : null)),       { name: 'Elevated Lower p80', color: '#8D6E63', thickness: 1, style: 'dotted' });
paint(horizontal_line(66),  { name: 'Strong Bullish', color: '#3A3A3A', style: 'dotted' });
paint(horizontal_line(33),  { name: 'Bullish Trend',  color: '#3A3A3A', style: 'dotted' });
paint(horizontal_line(0),   { name: 'Neutral',        color: '#888888', style: 'dotted' });
paint(horizontal_line(-33), { name: 'Bearish Trend',  color: '#3A3A3A', style: 'dotted' });
paint(horizontal_line(-66), { name: 'Strong Bearish', color: '#3A3A3A', style: 'dotted' });

// =====================================================================
// MODULE 9 — SIGNALS  (for scanner, alerts, strategy tester)
//   Names are fixed and must not collide with painted line names.
// =====================================================================
register_signal(discountOn,    'Fade Discount Active');
register_signal(thick,         'Structure Thick');
register_signal(for_every(density, (d) => (isNum(d) && d < DENS_THIN ? 1 : 0)), 'Structure Thin');
register_signal(bullExhaustOn, 'Bull Exhaustion Onset');
register_signal(bearExhaustOn, 'Bear Exhaustion Onset');
register_signal(pendingBottom, 'Bottom Pending');
register_signal(pendingTop,    'Top Pending');
register_signal(revUp,         'Reversal Up Confirmed');
register_signal(revDn,         'Reversal Down Confirmed');
register_signal(bearFail,      'Bear Exhaustion Failed (continuation)');
register_signal(bullFail,      'Bull Exhaustion Failed (continuation)');
register_signal(for_every(htfAgainst, (v) => (v >= 0.5 ? 1 : 0)), 'HTF Against Reversal');
register_signal(extended,      'Extended Either Side p95');
register_signal(for_every(composite, extended, (v, e) => (e === 1 && isNum(v) && v > 0 ? 1 : 0)), 'Extended Bullish');
register_signal(for_every(composite, extended, (v, e) => (e === 1 && isNum(v) && v < 0 ? 1 : 0)), 'Extended Bearish');
register_signal(relHigh,       'Rel Extension High (+2σ vs benchmark)');
register_signal(relLow,        'Rel Extension Low (-2σ vs benchmark)');
register_signal(relOverExt,    'Overextended vs Benchmark (gap closing)');
register_signal(relCatchUp,    'Laggard Catch-up vs Benchmark');
register_signal(for_every(composite, (v) => (isNum(v) && v >= 33 ? 1 : 0)),  'Composite Bullish (>=33)');
register_signal(for_every(composite, (v) => (isNum(v) && v <= -33 ? 1 : 0)), 'Composite Bearish (<=-33)');
</code>