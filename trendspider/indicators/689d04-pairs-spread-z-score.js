<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Pairs Spread Z-Score', 'lower', { shortName: 'Pairs Z+' });

/* =========================  Inputs  ========================= */
const ticker1 = input.symbol('Ticker 1 (y)', 'MMM');
const ticker2 = input.symbol('Ticker 2 (x)', 'AEP');
const betaMode  = input.select('Beta Mode', 'Fixed', ['Fixed', 'Auto OLS']);
const betaFixed = input.number('Beta (Fixed mode)', 1.35, { min: 0.01, max: 5, step: 0.01 });
const betaLen   = input.number('Beta Lookback (Auto OLS)', 120, { min: 20, max: 500, step: 1 });
const useLog    = input.select('Use Log Prices?', 'Yes', ['Yes','No']) === 'Yes';
const window    = input.number('Z-Score Lookback', 60, { min: 10, max: 500, step: 1 });
const upperThr  = input.number('Upper Entry Threshold',  2.0,  { min: 0.5, max: 5,   step: 0.1 });
const lowerThr  = input.number('Lower Entry Threshold', -2.0,  { min: -5,  max: -0.5, step: 0.1 });
const exitThr   = input.number('Exit Threshold (abs)',    0.5,  { min: 0.1, max: 2,   step: 0.1 });
const confirmN  = input.number('Confirm Bars',            1,    { min: 1,   max: 5,   step: 1 });
const hlLen     = input.number('Half-Life Lookback (bars)', 120, { min: 30, max: 500, step: 1 });
const closeOnlySel = input.select('Close-Only Mode', 'On', ['On','Off']);
const closeOnly    = (closeOnlySel === 'On');

/* =========================  Data fetch  ========================= */
const yRes = await request.history(ticker1, current.resolution);
assert(!yRes.error, `Error fetching data for ${ticker1}: ${yRes.error}`);
const xRes = await request.history(ticker2, current.resolution);
assert(!xRes.error, `Error fetching data for ${ticker2}: ${xRes.error}`);

/* =========================  Helpers  ========================= */
const lag1 = series => sliding_window_function(series, 2, vals => vals[0]);

const alignByChartTime = (y, yTime, x, xTime, chartTime) => {
  const yMap = {}; for (let i=0;i<yTime.length;i++) yMap[yTime[i]] = y[i];
  const xMap = {}; for (let i=0;i<xTime.length;i++) xMap[xTime[i]] = x[i];
  const yA = [], xA = [];
  for (let i=0;i<chartTime.length;i++) {
    const t = chartTime[i];
    yA.push(yMap[t] ?? null);
    xA.push(xMap[t] ?? null);
  }
  return [yA, xA];
};

const ols_beta = (yArr, xArr, N, fallback) => {
  const y = [], x = [];
  for (let i = Math.max(0, yArr.length - N); i < yArr.length; i++) {
    const yy = yArr[i], xx = xArr[i];
    if (yy != null && xx != null && isFinite(yy) && isFinite(xx)) { y.push(yy); x.push(xx); }
  }
  const n = x.length;
  if (n < 5) return fallback;
  let xSum=0, ySum=0, xx=0, xy=0;
  for (let i=0;i<n;i++){ xSum+=x[i]; ySum+=y[i]; xx+=x[i]*x[i]; xy+=x[i]*y[i]; }
  const den = n*xx - xSum*xSum;
  if (den === 0) return fallback;
  return (n*xy - xSum*ySum) / den;
};

const safeZ = (s, m, sd) => {
  if (s == null || m == null || sd == null) return null;
  if (!isFinite(sd) || sd === 0) return null;
  return (s - m) / sd;
};

const confirmBars = (condSeries, n) => 
  sliding_window_function(condSeries, n, vals => {
    for (let i=0;i<vals.length;i++) if (!vals[i]) return null;
    return 1;
  });

const ar1_half_life = (series, N) => {
  const s = [];
  for (let i=Math.max(0, series.length - N); i<series.length; i++) {
    const v = series[i];
    if (v != null && isFinite(v)) s.push(v);
  }
  if (s.length < 20) return { phi: null, hl: null };
  const y = [], x = [];
  for (let i=1;i<s.length;i++){ y.push(s[i]); x.push(s[i-1]); }
  let xSum=0,ySum=0,xx=0,xy=0, n=x.length;
  for (let i=0;i<n;i++){ xSum+=x[i]; ySum+=y[i]; xx+=x[i]*x[i]; xy+=x[i]*y[i]; }
  const den = n*xx - xSum*xSum;
  if (den === 0) return { phi: null, hl: null };
  const phi = (n*xy - xSum*ySum) / den;
  if (!isFinite(phi) || phi <= 0 || phi >= 1) return { phi, hl: null };
  const hl = -Math.log(2) / Math.log(phi);
  return { phi, hl };
};

/* =========================  Alignment & transforms  ========================= */
const chartTime = time;
const [yAlnRaw, xAlnRaw] = alignByChartTime(yRes.close, yRes.time, xRes.close, xRes.time, chartTime);

const yAligned0 = useLog ? for_every(yAlnRaw, v => (v!=null ? Math.log(v) : null)) : yAlnRaw;
const xAligned0 = useLog ? for_every(xAlnRaw, v => (v!=null ? Math.log(v) : null)) : xAlnRaw;

const yAligned = closeOnly ? lag1(yAligned0) : yAligned0;
const xAligned = closeOnly ? lag1(xAligned0) : xAligned0;

/* =========================  Beta & spread (close-only safe)  ========================= */
const beta =  (betaMode === 'Auto OLS')
    ? ols_beta(yAligned, xAligned, betaLen, betaFixed)
    : betaFixed;
const spread = for_every(yAligned, xAligned, (y, x) => (y!=null && x!=null ? y - beta * x : null));

/* =========================  Z-score (close-only safe)  ========================= */
const spreadMean = sma(spread, window);
const spreadStd  = stdev(spread, window);
const zScore     = for_every(spread, spreadMean, spreadStd, (s, m, sd) => safeZ(s, m, sd));

/* =========================  Signals (with confirm bars; close-only by construction)  ========================= */
const longCond  = for_every(zScore, z => (z!=null && z <  lowerThr) ? true : false);
const shortCond = for_every(zScore, z => (z!=null && z >  upperThr) ? true : false);
const exitCond  = for_every(zScore, z => (z!=null && Math.abs(z) < exitThr) ? true : false);
const longSignal  = confirmBars(longCond,  Math.max(1, confirmN));
const shortSignal = confirmBars(shortCond, Math.max(1, confirmN));
const exitSignal  = confirmBars(exitCond,  Math.max(1, confirmN));

/* =========================  Rolling half-life (info only)  ========================= */
const { phi, hl } = ar1_half_life(spread, hlLen);

/* =========================  Plots  ========================= */
paint(zScore, { name: "Spread Z-score", color: "blue" });
paint(horizontal_line(upperThr), { name: "Upper", color: "red",   style: "dotted" });
paint(horizontal_line(0),        { name: "Mean",  color: "gray",  style: "dotted" });
paint(horizontal_line(lowerThr), { name: "Lower", color: "green", style: "dotted" });
paint(horizontal_line( exitThr), { name: "Exit Upper", color: "silver", style: "line" });
paint(horizontal_line(-exitThr), { name: "Exit Lower", color: "silver", style: "line" });

/* =========================  Signals  ========================= */
register_signal(longSignal,  'Long');
register_signal(shortSignal, 'Short');
register_signal(exitSignal,  'Exit');

/* =========================  Labels (diagnostics)  ========================= */
const lastZ = zScore[zScore.length - 1];
const betaText = betaMode === 'Auto OLS' ? `β(rolling ${betaLen})` : `β(fixed)`;
paint_overlay('overlay', { position: 'bottom_right' }, {
    rows: [{
        cells: [
            { text: `Pair: ${ticker1}-${ticker2}`, color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5},
            { text: `${betaText}: ${Number(beta).toFixed(4)}`, color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5 },
            { text: `z: ${lastZ==null ? 'N/A' : lastZ.toFixed(2)}`, color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5},
            { text: `HL(${hlLen}): ${hl==null ? 'N/A' : hl.toFixed(1)} bars`, color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5 },
            { text: `Log: ${useLog ? 'Yes' : 'No'}`, color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5},
            { text: `Close-only: ${closeOnly ? 'On' : 'Off'}`, color: 'var(--text-color)', border: 'solid var(--border-color) 1px', padding: 5 }
        ]
    }]
});
</code>