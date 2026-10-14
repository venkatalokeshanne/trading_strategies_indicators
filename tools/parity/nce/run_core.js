// Runs core.js on Foresight-format CSVs (chart + higher timeframe) with the Pine defaults; prints JSON for check.py.
const fs = require("fs");
const { nceCompute, landHtf, nceEma } = require("./core.js");

const readCsv = (p) => {
    const rows = fs.readFileSync(p, "utf8").trim().split(/\r?\n/).slice(1).map((l) => l.split(","));
    return {
        t: rows.map((r) => Date.parse(`${r[1]}T${r[2]}Z`) / 1000),
        day: rows.map((r) => r[1]),
        o: rows.map((r) => +r[3]), h: rows.map((r) => +r[4]), l: rows.map((r) => +r[5]), c: rows.map((r) => +r[6]),
        v: rows.map((r) => +r[7]),
    };
};
const chart = readCsv(process.argv[2]);
// the higher timeframe: a CSV, or 4-hour bars built from the chart's own bars ("agg240-utc": clock-aligned in UTC;
// "agg240-session": the first four bars of each day, then the rest)
const aggregate = (src, keyOf) => {
    const out = { t: [], c: [] };
    let last = null;
    src.t.forEach((t, i) => {
        const k = keyOf(i);
        if (k !== last) { out.t.push(t); out.c.push(src.c[i]); last = k; } else out.c[out.c.length - 1] = src.c[i];
    });
    return out;
};
const mode = process.argv[3];
let htf;
if (mode === "agg240-utc") htf = aggregate(chart, (i) => Math.floor(chart.t[i] / 14400));
else if (mode === "agg240-session") {
    let k = 0;
    const seq = chart.day.map((d, i) => (i === 0 || d !== chart.day[i - 1] ? (k = 0) : ++k));
    htf = aggregate(chart, (i) => chart.day[i] + (seq[i] < 4 ? "a" : "b"));
} else if (mode === "agg240-local") {
    // TradingView's 240 bars for a US stock are anchored to the session: 09:30-13:30 and 13:30-16:00 New York time
    const nyOffset = (t) => {            // US daylight saving: second Sunday of March to first Sunday of November
        const d = new Date(t * 1000), y = d.getUTCFullYear();
        const nth = (m, k) => { const f = new Date(Date.UTC(y, m, 1)); return Date.UTC(y, m, 1 + ((7 - f.getUTCDay()) % 7) + 7 * (k - 1), 7) / 1000; };
        return t >= nth(2, 2) && t < nth(10, 1) ? -4 * 3600 : -5 * 3600;
    };
    htf = aggregate(chart, (i) => {
        const loc = chart.t[i] + nyOffset(chart.t[i]);
        const mins = Math.floor((loc % 86400) / 60);
        return Math.floor(loc / 86400) + (mins < 13 * 60 + 30 ? "a" : "b");
    });
} else if (mode === "agg240-first") {
    // as Foresight builds them: 4-hour buckets counted from each day's first bar
    let start = null;
    htf = aggregate(chart, (i) => {
        if (i === 0 || chart.day[i] !== chart.day[i - 1]) start = chart.t[i];
        return chart.day[i] + ":" + Math.floor((chart.t[i] - start) / 14400);
    });
} else htf = readCsv(mode);
const P = { threshold: 60, htfFilter: true, wtChannel: 9, wtAvg: 12, emaFast: 9, emaSlow: 21, emaBase: 50, atrLen: 14,
    slMult: 1.5, tp1Mult: 1.0, tp2Mult: 2.0, tp3Mult: 3.0, trail: true };
// UTC date = exchange date for US regular-hours bars (13:30-20:00 UTC)
const newSession = chart.day.map((d, i) => i === 0 || d !== chart.day[i - 1]);
const D = { o: chart.o, h: chart.h, l: chart.l, c: chart.c, v: chart.v, newSession,
    htfFast: landHtf(chart.t, htf.t, nceEma(htf.c, P.emaFast)), htfSlow: landHtf(chart.t, htf.t, nceEma(htf.c, P.emaSlow)) };
const r = nceCompute(D, P);
const b = (x) => x.map((v) => (v ? 1 : 0));
process.stdout.write(JSON.stringify({
    bullScore: r.bullScore, bearScore: r.bearScore, vwapVal: r.vwapVal, adxVal: r.adxVal, sqzMom: r.sqzMom,
    htfEmaFast: D.htfFast, htfEmaSlow: D.htfSlow, triggerBuyPlus: b(r.buyPlus), triggerSellPlus: b(r.sellPlus),
    rsiVal: r.rsiVal, histLine: r.histLine, wtTci: r.wtTci, atrVal: r.atrVal, tp1Hit: b(r.trade.tp1Hit),
    slHit: b(r.trade.slHit), tradeDir: r.trade.dir, ribbonFlipBull: b(r.flipBull), sqzFiring: b(r.sqzFiring),
    trailSL: r.trade.trail, sqzOn: b(r.sqzOn),
}));
