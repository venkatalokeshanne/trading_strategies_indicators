<code x-ref="code" class="hljs" data-clipboard-text>// Fractal Pressure + Levels — #TSBuild25
// On-chart: last confirmed fractal high/low as step lines.
// Lower panel: Fractal Pressure oscillator (0–100) = proximity to breaking levels, ATR-normalized.

describe_indicator('Fractal Pressure + Levels (#TSBuild25)');

// Inputs
const Span   = input.number('Fractal span (L/R)', 2,  { min: 2, max: 5 });
const AtrLen = input.number('ATR length',         14, { min: 5, max: 200 });
const Smooth = input.number('Osc smoothing',       3, { min: 0, max: 20  });
const ViewSm = input.number('View smoothing',      5, { min: 0, max: 30  });

// Helpers
const EPS = 1e-9;

// True Range EMA (ATR)
function atr_series(len){
  let prevC = null;
  const tr = for_every(high, low, close, (h, l, c) => {
    let a = (h - l);
    let b = (prevC === null) ? a : Math.abs(h - prevC);
    let d = (prevC === null) ? a : Math.abs(l - prevC);
    let trv = a; if (b > trv) trv = b; if (d > trv) trv = d;
    prevC = c;
    return trv;
  });
  return ema(tr, len);
}

// Last confirmed fractal high (step series)
function lastFractalHigh(span){
  let buf = [];
  let lastHi = null;
  return for_every(high, (h) => {
    buf.push(h);
    if (buf.length > (2*span+1)) buf.shift();
    if (buf.length === (2*span+1)){
      var c = span, mid = buf[c], isHi = true;
      for (var i=0;i<buf.length;i++){ if (i!==c && buf[i] > mid){ isHi=false; break; } }
      if (isHi) lastHi = mid;
    }
    return (lastHi === null) ? null : lastHi;
  });
}

// Last confirmed fractal low (step series)
function lastFractalLow(span){
  let buf = [];
  let lastLo = null;
  return for_every(low, (l) => {
    buf.push(l);
    if (buf.length > (2*span+1)) buf.shift();
    if (buf.length === (2*span+1)){
      var c = span, mid = buf[c], isLo = true;
      for (var i=0;i<buf.length;i++){ if (i!==c && buf[i] < mid){ isLo=false; break; } }
      if (isLo) lastLo = mid;
    }
    return (lastLo === null) ? null : lastLo;
  });
}

// Core
const fHigh = lastFractalHigh(Span);   // resistance
const fLow  = lastFractalLow(Span);    // support
const atrS  = atr_series(AtrLen);      // <— renamed

// Distances to levels (>=0)
const dRes = for_every(fHigh, close, (r, c) => (r==null)?null:Math.max(r - c, 0));
const dSup = for_every(fLow,  close, (s, c) => (s==null)?null:Math.max(c - s, 0));

// Normalize by ATR, compute tilt (-1..+1)
const nRes = for_every(dRes, atrS, (d, a) => (a && a>EPS) ? (d/a) : 0);
const nSup = for_every(dSup, atrS, (d, a) => (a && a>EPS) ? (d/a) : 0);
const rawTilt = for_every(nRes, nSup, (u, d) => {
  const up=u||0, down=d||0;
  return (down - up) / (down + up + EPS);
});

// Smooth & map to 0..100
const tiltSm   = (Smooth>0) ? ema(rawTilt, Smooth) : rawTilt;
const tilt01   = for_every(tiltSm, v => { let x=v; if(x>1)x=1; if(x<-1)x=-1; return (x+1)*50; });
const tiltView = (ViewSm>0) ? ema(tilt01, ViewSm) : tilt01;

// Plots
plot(fHigh,    { name: '__fp_res',  color: '#d07a7a' }); // on-chart line
plot(fLow,     { name: '__fp_sup',  color: '#5bb39b' }); // on-chart line

const g50 = for_every(close, _ => 50);
const g60 = for_every(close, _ => 60);
const g40 = for_every(close, _ => 40);

plot(g50,      { name: '__fp_g50',  color: '#666666' });
plot(g60,      { name: '__fp_g60',  color: '#3f63cc' });
plot(g40,      { name: '__fp_g40',  color: '#b94b4b' });
plot(tiltView, { name: '__fp_tilt', color: '#dddddd' });
// === Add-on: Breakout markers + Fractal Coil Width (ATR-normalized) ===

// 1) Coil width = (fractal high - fractal low) / ATR  → compression meter
const __fp_bandWidth   = for_every(fHigh, fLow, (r, s) => (r==null || s==null) ? null : Math.max(r - s, 0));
const __fp_coilRaw     = for_every(__fp_bandWidth, atrS, (w, a) => (a && a>EPS) ? (w / a) : null);
const __fp_coilSmooth  = (ViewSm>0) ? ema(__fp_coilRaw, ViewSm) : __fp_coilRaw;
plot(__fp_coilSmooth, { name: '__fp_coil', color: '#999999' }); // lower-pane companion to tilt

// 2) Breakout/Breakdown detection vs last confirmed fractals
//    We create boolean tracks and edge-detect them to fire once on the cross.

const __fp_above = for_every(close, fHigh, (c, r) => (r==null) ? 0 : (c > r ? 1 : 0));
const __fp_below = for_every(close, fLow,  (c, s) => (s==null) ? 0 : (c < s ? 1 : 0));

// edge detect "0 -> 1"
function __edgeRise(series){
  let prev = 0;
  return for_every(series, (v) => { const fire = (prev===0 && v===1) ? 1 : null; prev = v; return fire; });
}
const __fp_upEdge = __edgeRise(__fp_above);
const __fp_dnEdge = __edgeRise(__fp_below);

// place spike at price when edge fires
const __fp_upY = for_every(__fp_upEdge, close, (f, c) => f ? c : null);
const __fp_dnY = for_every(__fp_dnEdge, close, (f, c) => f ? c : null);

// plot the spikes (green for breakouts, red for breakdowns)
plot(__fp_upY, { name: '__fp_up', color: '#4cc38a' });
plot(__fp_dnY, { name: '__fp_dn', color: '#e25555' });
// === Make breakouts obvious: color the candle on the fire bar ===
// uses the edges you already built: __fp_upEdge / __fp_dnEdge
const __fp_barColor = for_every(__fp_upEdge, __fp_dnEdge, (u, d) => {
  return u ? '#22c55e' : (d ? '#ef4444' : null);  // green on breakout, red on breakdown
});
paint(candles, { color: __fp_barColor });
// coil-threshold shading on the oscillator pane (compression + pressure agreement)
const __fp_tiltHi = for_every(tiltView, v => v > 60 ? 1 : 0);
const __fp_tiltLo = for_every(tiltView, v => v < 40 ? 1 : 0);

// you already computed __fp_coilSmooth in my add-on; if not, paste that block first
const __fp_coilLow = for_every(__fp_coilSmooth, v => (v!=null && v < 0.6) ? 1 : 0); // <0.6 ATR-wide band = tight

// paint small columns in lower pane when compression + tilt align
const __fp_longSetup  = for_every(__fp_coilLow, __fp_tiltHi, (c,t) => (c&&t)?1:null);
const __fp_shortSetup = for_every(__fp_coilLow, __fp_tiltLo, (c,t) => (c&&t)?1:null);
plot(__fp_longSetup,  { name:'__fp_longSet',  color:'#4cc38a' });
plot(__fp_shortSetup, { name:'__fp_shortSet', color:'#e25555' });
</code>