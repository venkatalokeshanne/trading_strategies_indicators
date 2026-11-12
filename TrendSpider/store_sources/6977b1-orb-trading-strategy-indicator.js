<code x-ref="code" class="hljs" data-clipboard-text>// ============================================================================
// ORB Strategy (Auto) - Opening Range Breakout
// ============================================================================
// Fully automatic timeframe-independent indicator.
// OR window defaults to chart timeframe but can be overridden via Display OR Window.
// ALL signals, strategy entries, and visual lines use the same OR window.
// Lines extend to session close via projection. Supports 1m-60m charts.
//
// SESSION SUPPORT: Choose from NY Open, London Open, Asian Open, or Globex Open.
// All sessions are DST-aware via America/New_York timezone.
// ============================================================================

describe_indicator('ORB Trading Strategy Indicator', 'overlay');

const moment = library('moment-timezone');

// ==================== AUTO-DETECTION ====================

const chartTimeframe = parseInt(current.resolution, 10);
const isIntraday = !isNaN(chartTimeframe);
assert(isIntraday, 'This indicator requires an intraday chart (minute-based timeframe).');

// ==================== INPUTS ====================

const sessionChoice = input.select('Session', 'New York (9:30 AM ET)', [
    'New York (9:30 AM ET)',
    'London (3:00 AM ET)',
    'Asian (7:00 PM ET)',
    'Globex (6:00 PM ET)'
]);

// OR window override — controls BOTH what is drawn AND what signals fire against.
// 'Auto' matches chart timeframe.
const displayOverride = input.select('OR Window', 'Auto', ['Auto', '1', '5', '10', '15', '30', '60']);
const orWindowMinutes = displayOverride === 'Auto' ? chartTimeframe : parseInt(displayOverride, 10);

const supportedTFs = [1, 5, 10, 15, 30, 60];
if (displayOverride === 'Auto') {
    assert(
        supportedTFs.includes(chartTimeframe),
        `Chart timeframe (${chartTimeframe}m) not supported for Auto mode. Use 1m, 5m, 10m, 15m, 30m, or 60m — or set an OR Window override.`
    );
}

// Display
const showMidpoint    = input.boolean('Show OR Midpoint', false);
const showHistorical  = input.boolean('Show Historical Sessions', true);
const showEndLabels   = input.boolean('Show End-of-Line Labels', true);
const showEntryLabels = input.boolean('Show Entry Labels', true);

// Targets
const showR05 = input.boolean('Show 0.5R Targets', false);
const showR1  = input.boolean('Show 1R Targets', true);
const showR2  = input.boolean('Show 2R Targets', false);
const showR3  = input.boolean('Show 3R Targets', false);

// Colors
const colorORH          = input.color('ORH Color', '#22C55E');
const colorORL          = input.color('ORL Color', '#EF4444');
const colorMid          = input.color('OR Midpoint Color', '#94A3B8');
const colorLongTargets  = input.color('Long Targets Color', '#22C55E');
const colorShortTargets = input.color('Short Targets Color', '#EF4444');

// ==================== SESSION CONFIGURATION ====================
// All times in ET (America/New_York) — automatically DST-aware.

const SESSION_TZ = 'America/New_York';

let sessionStartHour, sessionStartMin;
let sessionEndHour, sessionEndMin;
let sessionLabel;

if (sessionChoice === 'New York (9:30 AM ET)') {
    sessionStartHour = 9;  sessionStartMin = 30;
    sessionEndHour   = 16; sessionEndMin   = 0;
    sessionLabel = 'NY';
} else if (sessionChoice === 'London (3:00 AM ET)') {
    sessionStartHour = 3;  sessionStartMin = 0;
    sessionEndHour   = 12; sessionEndMin   = 0;
    sessionLabel = 'LDN';
} else if (sessionChoice === 'Asian (7:00 PM ET)') {
    sessionStartHour = 19; sessionStartMin = 0;
    sessionEndHour   = 4;  sessionEndMin   = 0;
    sessionLabel = 'ASIA';
} else if (sessionChoice === 'Globex (6:00 PM ET)') {
    sessionStartHour = 18; sessionStartMin = 0;
    sessionEndHour   = 17; sessionEndMin   = 0;
    sessionLabel = 'GBX';
}

const sessionStartMinutes = sessionStartHour * 60 + sessionStartMin;
const sessionEndMinutes   = sessionEndHour * 60 + sessionEndMin;
const sessionCrossesMidnight = sessionEndMinutes <= sessionStartMinutes;

// ==================== CONSTANTS ====================

const LABEL_STYLE_OR     = { border_width: 1, border_radius: 3, border_color: '#374151', background_color: '#111827' };
const LABEL_STYLE_TARGET = { border_width: 1, border_radius: 3, border_color: '#374151', background_color: '#111827' };

// ==================== HELPERS ====================

function seriesOrNull(enabled, s) { return enabled ? s : series_of(null); }

function getETMinutes(ts) {
    const m = moment.tz(ts * 1000, SESSION_TZ);
    return m.hour() * 60 + m.minute();
}

function isWithinSession(ts) {
    const timeVal = getETMinutes(ts);
    if (sessionCrossesMidnight) {
        return timeVal >= sessionStartMinutes || timeVal < sessionEndMinutes;
    }
    return timeVal >= sessionStartMinutes && timeVal < sessionEndMinutes;
}

function getSessionDayKey(ts) {
    const m = moment.tz(ts * 1000, SESSION_TZ);
    const timeVal = m.hour() * 60 + m.minute();
    if (sessionCrossesMidnight && timeVal < sessionEndMinutes) {
        return m.clone().subtract(1, 'day').format('YYYY-MM-DD');
    }
    return m.format('YYYY-MM-DD');
}

function getORWindowStart(dayKey) {
    const m = moment.tz(dayKey, 'YYYY-MM-DD', SESSION_TZ);
    m.hour(sessionStartHour);
    m.minute(sessionStartMin);
    m.second(0);
    return m.unix();
}

function lastDefinedIndex(s) {
    for (let i = s.length - 1; i >= 0; i--) {
        if (s[i] !== null && s[i] !== undefined) return i;
    }
    return -1;
}

function labelEndOfLineSafe(enabled, paintedLine, series, text, color, labelStyle) {
    if (!showEndLabels) return;
    const idx = lastDefinedIndex(enabled ? series : series_of(null));
    if (idx < 0) return;
    paint_label_at_line(paintedLine, idx, text, { ...labelStyle, color });
}

// ==================== STATE ARRAYS ====================

const stateORBuilding    = series_of(false);
const stateORLockedToday = series_of(false);
const stateRTHActive     = series_of(false);

// Unified OR levels — used for BOTH signals and visuals
const orhLevel   = series_of(null);
const orlLevel   = series_of(null);
const orMidLevel = series_of(null);

const upR05Level = series_of(null);
const upR1Level  = series_of(null);
const upR2Level  = series_of(null);
const upR3Level  = series_of(null);

const dnR05Level = series_of(null);
const dnR1Level  = series_of(null);
const dnR2Level  = series_of(null);
const dnR3Level  = series_of(null);

const longStopLevel  = series_of(null);
const shortStopLevel = series_of(null);

// Visual arrays (only populated during visible session candles)
const orhVisual   = series_of(null);
const orlVisual   = series_of(null);
const orMidVisual = series_of(null);

const upR05Visual = series_of(null);
const upR1Visual  = series_of(null);
const upR2Visual  = series_of(null);
const upR3Visual  = series_of(null);

const dnR05Visual = series_of(null);
const dnR1Visual  = series_of(null);
const dnR2Visual  = series_of(null);
const dnR3Visual  = series_of(null);

// Day tracking
const dayKeySeries       = series_of(null);
const isCurrentDaySeries = series_of(false);

// ==================== PASS 1: COMPUTE OR LEVELS ====================
// Single pass using orWindowMinutes for everything (signals + visuals).

let currentDayKey    = null;
let orWindowStartTs  = null;
let orWindowEndTs    = null;
let sessionORHigh    = null;
let sessionORLow     = null;
let sessionORLocked  = false;

let carryORH = null, carryORL = null, carryMid = null;
let carryUpR05 = null, carryUpR1 = null, carryUpR2 = null, carryUpR3 = null;
let carryDnR05 = null, carryDnR1 = null, carryDnR2 = null, carryDnR3 = null;

const lastDayKey = getSessionDayKey(time[time.length - 1]);

for (let i = 0; i < time.length; i++) {
    const ts     = time[i];
    const dayKey = getSessionDayKey(ts);

    dayKeySeries[i]       = dayKey;
    isCurrentDaySeries[i] = (dayKey === lastDayKey);

    if (dayKey !== currentDayKey) {
        currentDayKey = dayKey;
        orWindowStartTs = getORWindowStart(dayKey);
        orWindowEndTs   = orWindowStartTs + orWindowMinutes * 60;
        sessionORHigh   = null;
        sessionORLow    = null;
        sessionORLocked = false;
    }

    const inRTH          = isWithinSession(ts);
    stateRTHActive[i]    = inRTH;
    const withinORWindow = ts >= orWindowStartTs && ts < orWindowEndTs;
    const pastORWindow   = ts >= orWindowEndTs;

    if (withinORWindow && inRTH) {
        stateORBuilding[i]    = true;
        stateORLockedToday[i] = false;
        sessionORHigh = sessionORHigh === null ? high[i] : Math.max(sessionORHigh, high[i]);
        sessionORLow  = sessionORLow  === null ? low[i]  : Math.min(sessionORLow,  low[i]);

    } else if (pastORWindow && inRTH && !sessionORLocked && sessionORHigh !== null && sessionORLow !== null) {
        sessionORLocked       = true;
        stateORBuilding[i]    = false;
        stateORLockedToday[i] = true;

        const range = sessionORHigh - sessionORLow;
        carryORH = sessionORHigh;
        carryORL = sessionORLow;
        carryMid = (carryORH + carryORL) / 2;

        if (range > 0) {
            carryUpR05 = carryORH + range * 0.5; carryUpR1 = carryORH + range * 1.0;
            carryUpR2  = carryORH + range * 2.0; carryUpR3 = carryORH + range * 3.0;
            carryDnR05 = carryORL - range * 0.5; carryDnR1 = carryORL - range * 1.0;
            carryDnR2  = carryORL - range * 2.0; carryDnR3 = carryORL - range * 3.0;
        } else {
            carryUpR05 = carryUpR1 = carryUpR2 = carryUpR3 = null;
            carryDnR05 = carryDnR1 = carryDnR2 = carryDnR3 = null;
        }

    } else if (sessionORLocked) {
        stateORBuilding[i]    = false;
        stateORLockedToday[i] = inRTH;
    }

    // Unified level series (carry-forward for signals)
    orhLevel[i]   = carryORH; orlLevel[i]   = carryORL;
    orMidLevel[i] = carryMid;

    upR05Level[i] = carryUpR05; upR1Level[i] = carryUpR1;
    upR2Level[i]  = carryUpR2;  upR3Level[i] = carryUpR3;
    dnR05Level[i] = carryDnR05; dnR1Level[i] = carryDnR1;
    dnR2Level[i]  = carryDnR2;  dnR3Level[i] = carryDnR3;

    longStopLevel[i]  = carryORL;
    shortStopLevel[i] = carryORH;

    // Visual arrays (only show during session)
    const show = showHistorical
        ? (inRTH && (stateORBuilding[i] || sessionORLocked))
        : (isCurrentDaySeries[i] && inRTH && (stateORBuilding[i] || sessionORLocked));

    if (show) {
        if (stateORBuilding[i] && sessionORHigh !== null && sessionORLow !== null) {
            orhVisual[i] = sessionORHigh;
            orlVisual[i] = sessionORLow;
            orMidVisual[i] = (sessionORHigh + sessionORLow) / 2;
        } else if (sessionORLocked) {
            orhVisual[i]   = carryORH;   orlVisual[i]   = carryORL;
            orMidVisual[i] = carryMid;
            upR05Visual[i] = carryUpR05; upR1Visual[i]  = carryUpR1;
            upR2Visual[i]  = carryUpR2;  upR3Visual[i]  = carryUpR3;
            dnR05Visual[i] = carryDnR05; dnR1Visual[i]  = carryDnR1;
            dnR2Visual[i]  = carryDnR2;  dnR3Visual[i]  = carryDnR3;
        }
    }
}

// ==================== PASS 2: DETECT ENTRIES (ONE PER SESSION) ====================

const orbLongEntry  = series_of(false);
const orbShortEntry = series_of(false);

let sessionHadEntry    = false;
let currentSessionKey  = null;

for (let i = 1; i < time.length; i++) {
    const dayKey = dayKeySeries[i];
    if (dayKey !== currentSessionKey) { currentSessionKey = dayKey; sessionHadEntry = false; }

    const prevClose = close[i - 1], currClose = close[i];
    const orh = orhLevel[i], orl = orlLevel[i];
    const locked = stateORLockedToday[i];

    if (!sessionHadEntry && orh !== null && orl !== null && prevClose !== null && locked) {
        if (prevClose <= orh && currClose > orh) {
            orbLongEntry[i] = true; sessionHadEntry = true;
        } else if (prevClose >= orl && currClose < orl) {
            orbShortEntry[i] = true; sessionHadEntry = true;
        }
    }
}

// ==================== PASS 3: SCANNER SIGNALS ====================

const scannerLongEntry  = series_of(false);
const scannerShortEntry = series_of(false);

let scanSessionHadEntry   = false;
let scanCurrentSessionKey = null;

for (let i = 0; i < time.length; i++) {
    const dayKey = dayKeySeries[i];
    if (dayKey !== scanCurrentSessionKey) { scanCurrentSessionKey = dayKey; scanSessionHadEntry = false; }

    const orh = orhLevel[i], orl = orlLevel[i];
    const locked = stateORLockedToday[i];

    if (!scanSessionHadEntry && isCurrentDaySeries[i] && orh !== null && orl !== null && locked) {
        if (high[i] > orh)  { scannerLongEntry[i]  = true; scanSessionHadEntry = true; }
        else if (low[i] < orl) { scannerShortEntry[i] = true; scanSessionHadEntry = true; }
    }
}

// ==================== PASS 4: STOP LOSS HITS ====================

const longStopHit  = series_of(false);
const shortStopHit = series_of(false);

for (let i = 1; i < time.length; i++) {
    const orl = orlLevel[i], orh = orhLevel[i];
    if (orl !== null && low[i - 1]  !== null && low[i - 1]  >= orl && low[i]  < orl) longStopHit[i]  = true;
    if (orh !== null && high[i - 1] !== null && high[i - 1] <= orh && high[i] > orh) shortStopHit[i] = true;
}

// ==================== PASS 5: TARGET HITS ====================

const longTarget05Hit  = series_of(false), longTarget1Hit  = series_of(false);
const longTarget2Hit   = series_of(false), longTarget3Hit  = series_of(false);
const shortTarget05Hit = series_of(false), shortTarget1Hit = series_of(false);
const shortTarget2Hit  = series_of(false), shortTarget3Hit = series_of(false);

for (let i = 1; i < time.length; i++) {
    const pH = high[i - 1], cH = high[i];
    const pL = low[i - 1],  cL = low[i];

    const l05 = upR05Level[i]; if (l05 !== null && pH !== null && pH < l05 && cH >= l05) longTarget05Hit[i]  = true;
    const l1  = upR1Level[i];  if (l1  !== null && pH !== null && pH < l1  && cH >= l1)  longTarget1Hit[i]   = true;
    const l2  = upR2Level[i];  if (l2  !== null && pH !== null && pH < l2  && cH >= l2)  longTarget2Hit[i]   = true;
    const l3  = upR3Level[i];  if (l3  !== null && pH !== null && pH < l3  && cH >= l3)  longTarget3Hit[i]   = true;

    const s05 = dnR05Level[i]; if (s05 !== null && pL !== null && pL > s05 && cL <= s05) shortTarget05Hit[i] = true;
    const s1  = dnR1Level[i];  if (s1  !== null && pL !== null && pL > s1  && cL <= s1)  shortTarget1Hit[i]  = true;
    const s2  = dnR2Level[i];  if (s2  !== null && pL !== null && pL > s2  && cL <= s2)  shortTarget2Hit[i]  = true;
    const s3  = dnR3Level[i];  if (s3  !== null && pL !== null && pL > s3  && cL <= s3)  shortTarget3Hit[i]  = true;
}

// ==================== PASS 6: SESSION EXIT ====================
// Fires on BOTH the last candle inside the session (EOD exit) AND
// the first candle outside the session (backup). This ensures the
// Strategy Tester always gets at least one exit signal per session.

const sessionExit = series_of(false);

// 6a: EOD exit — last candle inside session
let exitTimeMinutes;
if (sessionCrossesMidnight) {
    exitTimeMinutes = sessionEndMinutes - chartTimeframe;
    if (exitTimeMinutes < 0) exitTimeMinutes += 24 * 60;
} else {
    exitTimeMinutes = sessionEndMinutes - chartTimeframe;
}

let eodExitFiredThisSession = false;
let currentEodSessionKey    = null;

for (let i = 0; i < time.length; i++) {
    const dayKey = dayKeySeries[i];
    if (dayKey !== currentEodSessionKey) { currentEodSessionKey = dayKey; eodExitFiredThisSession = false; }

    const candleMinutes = getETMinutes(time[i]);

    let pastExitTime = false;
    if (sessionCrossesMidnight) {
        if (exitTimeMinutes >= sessionStartMinutes) {
            pastExitTime = (candleMinutes >= exitTimeMinutes) ||
                           (candleMinutes < sessionEndMinutes);
        } else {
            pastExitTime = (candleMinutes >= exitTimeMinutes && candleMinutes < sessionEndMinutes);
        }
    } else {
        pastExitTime = candleMinutes >= exitTimeMinutes;
    }

    if (stateRTHActive[i] && !eodExitFiredThisSession && pastExitTime) {
        sessionExit[i] = true;
        eodExitFiredThisSession = true;
    }
}

// 6b: Backup — first candle outside session after being inside
for (let i = 1; i < time.length; i++) {
    if (stateRTHActive[i - 1] && !stateRTHActive[i]) {
        sessionExit[i] = true;
    }
}

// ==================== PASS 7: SAFE ENTRY WINDOW ====================

const safeEntryWindow = series_of(false);

let entryCutoffMinutes;
if (sessionCrossesMidnight) {
    entryCutoffMinutes = sessionEndMinutes - Math.floor(orWindowMinutes * 3.5);
    if (entryCutoffMinutes < 0) entryCutoffMinutes += 24 * 60;
} else {
    entryCutoffMinutes = sessionEndMinutes - Math.floor(orWindowMinutes * 3.5);
}

for (let i = 0; i < time.length; i++) {
    const candleMinutes = getETMinutes(time[i]);

    let beforeCutoff = false;
    if (sessionCrossesMidnight) {
        if (entryCutoffMinutes >= sessionStartMinutes) {
            beforeCutoff = (candleMinutes >= sessionStartMinutes && candleMinutes < entryCutoffMinutes);
        } else {
            beforeCutoff = (candleMinutes >= sessionStartMinutes) ||
                           (candleMinutes < entryCutoffMinutes);
        }
    } else {
        beforeCutoff = candleMinutes < entryCutoffMinutes;
    }

    if (stateORLockedToday[i] && stateRTHActive[i] && beforeCutoff) {
        safeEntryWindow[i] = true;
    }
}

// ==================== SIGNAL REGISTRATION ====================

register_signal(orbLongEntry,    'Entry: Long (Strategy)');
register_signal(orbShortEntry,   'Entry: Short (Strategy)');
register_signal(scannerLongEntry,  'Entry: Long (Scan)');
register_signal(scannerShortEntry, 'Entry: Short (Scan)');
register_signal(safeEntryWindow,   'Safe Entry Window');

register_signal(longStopHit,   'Stop: Long');
register_signal(shortStopHit,  'Stop: Short');

register_signal(longTarget05Hit,  'Target: Long 0.5R');
register_signal(longTarget1Hit,   'Target: Long 1R');
register_signal(longTarget2Hit,   'Target: Long 2R');
register_signal(longTarget3Hit,   'Target: Long 3R');
register_signal(shortTarget05Hit, 'Target: Short 0.5R');
register_signal(shortTarget1Hit,  'Target: Short 1R');
register_signal(shortTarget2Hit,  'Target: Short 2R');
register_signal(shortTarget3Hit,  'Target: Short 3R');

register_signal(sessionExit, 'Session Exit');

// ==================== PAINTING ====================

const pORH = paint(orhVisual, { name: 'ORH (Long Breakout)', style: 'ladder', color: colorORH, thickness: 2 });
const pORL = paint(orlVisual, { name: 'ORL (Short Breakdown)', style: 'ladder', color: colorORL, thickness: 2 });

const pMid     = paint(seriesOrNull(showMidpoint, orMidVisual), { name: 'OR Midpoint',      style: 'ladder', color: colorMid, thickness: 1 });

const pLongR05 = paint(seriesOrNull(showR05, upR05Visual), { name: 'Long 0.5R Target',  style: 'ladder', color: colorLongTargets,  thickness: 1 });
const pLongR1  = paint(seriesOrNull(showR1,  upR1Visual),  { name: 'Long 1R Target',    style: 'ladder', color: colorLongTargets,  thickness: 1 });
const pLongR2  = paint(seriesOrNull(showR2,  upR2Visual),  { name: 'Long 2R Target',    style: 'ladder', color: colorLongTargets,  thickness: 1 });
const pLongR3  = paint(seriesOrNull(showR3,  upR3Visual),  { name: 'Long 3R Target',    style: 'ladder', color: colorLongTargets,  thickness: 1 });

const pShortR05 = paint(seriesOrNull(showR05, dnR05Visual), { name: 'Short 0.5R Target', style: 'ladder', color: colorShortTargets, thickness: 1 });
const pShortR1  = paint(seriesOrNull(showR1,  dnR1Visual),  { name: 'Short 1R Target',   style: 'ladder', color: colorShortTargets, thickness: 1 });
const pShortR2  = paint(seriesOrNull(showR2,  dnR2Visual),  { name: 'Short 2R Target',   style: 'ladder', color: colorShortTargets, thickness: 1 });
const pShortR3  = paint(seriesOrNull(showR3,  dnR3Visual),  { name: 'Short 3R Target',   style: 'ladder', color: colorShortTargets, thickness: 1 });

// End-of-line labels
labelEndOfLineSafe(true,         pORH,     orhVisual,   `ORH [${sessionLabel}]`, colorORH,          LABEL_STYLE_OR);
labelEndOfLineSafe(true,         pORL,     orlVisual,   `ORL [${sessionLabel}]`, colorORL,          LABEL_STYLE_OR);
labelEndOfLineSafe(showMidpoint, pMid,     orMidVisual, 'MID',                   colorMid,          LABEL_STYLE_OR);

labelEndOfLineSafe(showR05, pLongR05,  upR05Visual, '0.5R', colorLongTargets,  LABEL_STYLE_TARGET);
labelEndOfLineSafe(showR1,  pLongR1,   upR1Visual,  '1R',   colorLongTargets,  LABEL_STYLE_TARGET);
labelEndOfLineSafe(showR2,  pLongR2,   upR2Visual,  '2R',   colorLongTargets,  LABEL_STYLE_TARGET);
labelEndOfLineSafe(showR3,  pLongR3,   upR3Visual,  '3R',   colorLongTargets,  LABEL_STYLE_TARGET);

labelEndOfLineSafe(showR05, pShortR05, dnR05Visual, '0.5R', colorShortTargets, LABEL_STYLE_TARGET);
labelEndOfLineSafe(showR1,  pShortR1,  dnR1Visual,  '1R',   colorShortTargets, LABEL_STYLE_TARGET);
labelEndOfLineSafe(showR2,  pShortR2,  dnR2Visual,  '2R',   colorShortTargets, LABEL_STYLE_TARGET);
labelEndOfLineSafe(showR3,  pShortR3,  dnR3Visual,  '3R',   colorShortTargets, LABEL_STYLE_TARGET);

// ==================== PROJECTIONS (EXTEND TO SESSION CLOSE) ====================

const lastTs            = time[time.length - 1];
const lastCandleMinutes = getETMinutes(lastTs);
const lastCandleInRTH   = stateRTHActive[time.length - 1];

let minutesRemaining = 0;
if (lastCandleInRTH && carryORH !== null) {
    if (sessionCrossesMidnight) {
        if (lastCandleMinutes >= sessionStartMinutes) {
            minutesRemaining = (24 * 60 - lastCandleMinutes) + sessionEndMinutes;
        } else {
            minutesRemaining = sessionEndMinutes - lastCandleMinutes;
        }
    } else {
        minutesRemaining = sessionEndMinutes - lastCandleMinutes;
    }
}

if (lastCandleInRTH && carryORH !== null && minutesRemaining > 0) {
    const candlesRemaining = Math.max(1, Math.ceil(minutesRemaining / chartTimeframe));

    paint_projection(pORH, Array(candlesRemaining).fill(carryORH));
    paint_projection(pORL, Array(candlesRemaining).fill(carryORL));

    if (showMidpoint && carryMid !== null) {
        paint_projection(pMid, Array(candlesRemaining).fill(carryMid));
    }
    if (showR05) {
        if (carryUpR05 !== null) paint_projection(pLongR05,  Array(candlesRemaining).fill(carryUpR05));
        if (carryDnR05 !== null) paint_projection(pShortR05, Array(candlesRemaining).fill(carryDnR05));
    }
    if (showR1) {
        if (carryUpR1 !== null) paint_projection(pLongR1,  Array(candlesRemaining).fill(carryUpR1));
        if (carryDnR1 !== null) paint_projection(pShortR1, Array(candlesRemaining).fill(carryDnR1));
    }
    if (showR2) {
        if (carryUpR2 !== null) paint_projection(pLongR2,  Array(candlesRemaining).fill(carryUpR2));
        if (carryDnR2 !== null) paint_projection(pShortR2, Array(candlesRemaining).fill(carryDnR2));
    }
    if (showR3) {
        if (carryUpR3 !== null) paint_projection(pLongR3,  Array(candlesRemaining).fill(carryUpR3));
        if (carryDnR3 !== null) paint_projection(pShortR3, Array(candlesRemaining).fill(carryDnR3));
    }
}

// ==================== ENTRY LABELS ====================

const longEntryLabels  = for_every(orbLongEntry,  (s) => s ? 'LONG'  : null);
const shortEntryLabels = for_every(orbShortEntry, (s) => s ? 'SHORT' : null);

paint(seriesOrNull(showEntryLabels, longEntryLabels), {
    style: 'labels_below', name: 'Long Entry',
    color: '#FFFFFF', backgroundColor: '#22C55E', fontSize: 11, verticalOffset: 5
});

paint(seriesOrNull(showEntryLabels, shortEntryLabels), {
    style: 'labels_above', name: 'Short Entry',
    color: '#FFFFFF', backgroundColor: '#EF4444', fontSize: 11, verticalOffset: 5
});</code>