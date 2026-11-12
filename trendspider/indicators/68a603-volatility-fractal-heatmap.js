<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Volatility Fractal Heatmap #TSBuild25', 'price', {
  shortName: 'VF Heatmap',
  decimals: 2
});

/* ================== Inputs ================== */
const grpCore  = '① Core';
const grpBand  = '② Bands';
const grpDisp  = '③ Display';

const lenS   = input.number('Short ATR Len', 10, { min: 2, step: 1, group: grpCore });
const lenM   = input.number('Mid ATR Len',   21, { min: 2, step: 1, group: grpCore });
const lenL   = input.number('Long ATR Len',  50, { min: 2, step: 1, group: grpCore });

const zWin   = input.number('Z-Score Window', 200, { min: 50, step: 10, group: grpCore });
const smooth = input.number('Heat Smooth',       5, { min: 1,  step: 1,  group: grpCore });

const bandMult = input.number('Band Mult (ATR-blend)', 1.5, { min: 0.1, step: 0.1, group: grpBand });
const showBands = input.boolean('Show Bands', true, { group: grpBand });

const pressureZ  = input.number('Pressure Z Threshold', 1.25, { min: 0.5, step: 0.05, group: grpDisp });
const showDots   = input.boolean('Show Pressure Dots', true,  { group: grpDisp });

/* ================== Helpers ================== */
const move = (s, k) => {
  const out = series_of(null);
  for (let i=0;i<s.length;i++){ const j=i-k; out[i]= (j>=0? s[j]: null); }
  return out;
};

const ema_ts = (s, length) => {
  const out = series_of(null);
  if (length < 1) return out;
  const a = 2.0/(length+1.0);
  let prev = null;
  for (let i=0;i<s.length;i++){
    const v = s[i];
    if (v==null) { out[i] = (i>0? out[i-1]: null); continue; }
    prev = (prev==null? v: a*v + (1-a)*prev);
    out[i] = prev;
  }
  return out;
};

const trueRange = (() => {
  const pc = move(close,1);
  const out = series_of(null);
  for (let i=0;i<time.length;i++){
    if (i===0) { out[i]=null; continue; }
    const a = (high[i]!=null && low[i]!=null) ? Math.abs(high[i]-low[i]) : null;
    const b = (high[i]!=null && pc[i]!=null)  ? Math.abs(high[i]-pc[i])  : null;
    const c = (low[i]!=null  && pc[i]!=null)  ? Math.abs(low[i]-pc[i])   : null;
    const m = Math.max(a??-Infinity, b??-Infinity, c??-Infinity);
    out[i]  = (m===-Infinity? null: m);
  }
  return out;
})();

const atrr = (len) => ema_ts(trueRange, len);

const zscore = (s, win) => {
  const m = sma(s, win);
  const sd = stdev(s, win);
  return for_every(s, m, sd, (v, mm, ss) => {
    if (v==null || mm==null || ss==null || !isFinite(ss) || ss===0) return null;
    return (v - mm)/ss;
  });
};

const sma_ts = (s, n) => sma(s, Math.max(1,n));

const clamp01 = t => Math.max(0, Math.min(1, t));
const lerp = (a,b,t)=> a + (b-a)*t;

/* ================== Core calc ================== */
const atrS = atrr(lenS);
const atrM = atrr(lenM);
const atrL = atrr(lenL);

// Z of ATRs (abs => intensity of volatility)
const zS = zscore(atrS, zWin);
const zM = zscore(atrM, zWin);
const zL = zscore(atrL, zWin);

const heatRaw = for_every(zS, zM, zL, (a,b,c)=>{
  const aa = a==null?0:Math.abs(a);
  const bb = b==null?0:Math.abs(b);
  const cc = c==null?0:Math.abs(c);
  return (aa + bb + cc)/3.0; // avg |z|
});
const heat = sma_ts(heatRaw, smooth);

// blended ATR for bands (weighted by relative intensity)
const wS = 1.0, wM = 1.2, wL = 1.5;
const atrBlend = for_every(atrS, atrM, atrL, (a,b,c)=>{
  if (a==null || b==null || c==null) return null;
  return (wS*a + wM*b + wL*c)/(wS+wM+wL);
});

// Bands around price
const upper = for_every(close, atrBlend, (c,a)=> (c!=null && a!=null) ? c + bandMult*a : null);
const lower = for_every(close, atrBlend, (c,a)=> (c!=null && a!=null) ? c - bandMult*a : null);

/* ================== Colors & dots ================== */
function colorFromHeat(h){
  if (h==null) return null;
  // Map heat 0..3 (typical) into gradient: gray → orange → red
  const t = clamp01(Math.min(3, Math.max(0, h))/3.0);
  // simple two‑stop: gray(#C6C5C5) → red(#FF2D2D)
  // add mid orange morph
  const midT = t<0.5 ? (t/0.5) : ((t-0.5)/0.5);
  if (t < 0.5) {
    // gray → orange(#FFA500)
    const c1 = [198,197,197], c2=[255,165,0];
    const r = lerp(c1[0],c2[0], midT), g=lerp(c1[1],c2[1], midT), b=lerp(c1[2],c2[2], midT);
    return `#${Math.round(r).toString(16).padStart(2,'0')}${Math.round(g).toString(16).padStart(2,'0')}${Math.round(b).toString(16).padStart(2,'0')}`.toUpperCase();
  } else {
    // orange → red(#FF2D2D)
    const c1=[255,165,0], c2=[255,45,45];
    const r = lerp(c1[0],c2[0], midT), g=lerp(c1[1],c2[1], midT), b=lerp(c1[2],c2[2], midT);
    return `#${Math.round(r).toString(16).padStart(2,'0')}${Math.round(g).toString(16).padStart(2,'0')}${Math.round(b).toString(16).padStart(2,'0')}`.toUpperCase();
  }
}

const candleColors = for_every(heat, h => colorFromHeat(h));
color_candles(candleColors);

if (showBands){
  paint(upper, { name: 'VF Upper', color: '#FF7F50', style: 'line', thickness: 1 });
  paint(lower, { name: 'VF Lower', color: '#FF7F50', style: 'line', thickness: 1 });
}

/* Pressure dots when heat ≥ threshold Z on any leg */
const press = for_every(zS, zM, zL, (a,b,c)=>{
  const cond = (a!=null && a>=pressureZ) || (b!=null && b>=pressureZ) || (c!=null && c>=pressureZ);
  return cond? low : null;
});
if (showDots) paint(press, { name: 'Pressure Dots', color: '#FF007A', style: 'dotted', thickness: 3 });

/* ============== Scanner Signals ============== */
const sig_VolPressure = for_every(zS, zM, zL, (a,b,c)=> {
  const ok = (a!=null && a>=pressureZ) || (b!=null && b>=pressureZ) || (c!=null && c>=pressureZ);
  return ok? true: false;
});
const sig_BandTouch = for_every(close, upper, lower, (c,u,l)=>{
  if (c==null || u==null || l==null) return false;
  return (c>=u || c<=l);
});
register_signal(sig_VolPressure, 'VF: Vol Pressure ≥ Z');
register_signal(sig_BandTouch,   'VF: Touch Band');
</code>