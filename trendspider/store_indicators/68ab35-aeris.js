<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('AERIS', 'lower', { warmup: 300 });

// AERIS — Asymmetry & Efficiency Regime Inference System (v1.1)
// Distinct visuals: score as line by default, parts off by default, subtle guides.

// ===== Inputs (short labels) =====
const fastLen   = input.number('EMA fast', 21, { min: 1, max: 500 });
const slowLen   = input.number('EMA slow', 89, { min: 1, max: 500 });
const atrLen    = input.number('ATR len',  14, { min: 1, max: 500 });
const zLen      = input.number('Z len',   100, { min: 20, max: 1000 });
const thLong    = input.number('Go long', 65, { min: 0, max: 100 });
const thShort   = input.number('Go short',35, { min: 0, max: 100 });
const scoreAsLine = input.boolean('Score as line', true);   // NEW: default line
const showParts   = input.boolean('Show parts',    false);  // NEW: default off
const lineWidth   = input.number('Line width',     2, { min:1, max:5 });

// Colors
const cUp   = input.color('Up col',   '#00c853');
const cDn   = input.color('Dn col',   '#d32f2f');
const cMid  = input.color('Mid col',  '#9e9e9e');
const cA    = input.color('A col',    '#42a5f5');  // Asym
const cE    = input.color('E col',    '#ffa000');  // Eff
const cT    = input.color('T col',    '#ab47bc');  // Tilt
const cN    = input.color('N col',    '#26a69a');  // eNergy
const cG    = input.color('Guide',    '#616161');  // subtle guides

// ===== Helpers =====
function zscore(s, n){ const m=sma(s,n), sd=stdev(s,n); return div(sub(s,m), add(sd, series_of(1e-9))); }
function clamp3(s){ return for_every(s, x => (x==null)?null:(x>3?3:(x<-3?-3:x))); }
function to100(sZ){ const cz=clamp3(sZ); return add(mult(div(cz,series_of(3)),series_of(50)),series_of(50)); }
function absS(s){ return for_every(s, x => (x==null?null:Math.abs(x))); }
function sqrtS(s){ return for_every(s, x => (x==null?null:Math.sqrt(x))); }
function guide(val, name){ paint(series_of(val), { name, color:cG, style: 'dotted' }); }

// ===== Core series =====
const rng  = sub(high, low);
const body = sub(close, open);
const atrV = atr(atrLen);

// Wick geometry
const upRef = for_every(open, close, (o,c)=> (o>c?o:c));
const dnRef = for_every(open, close, (o,c)=> (o<c?o:c));
const upW   = sub(high, upRef);
const dnW   = sub(dnRef, low);

// 1) Asymmetry
const wickBias = div(sub(dnW, upW), add(rng, series_of(1e-9)));  // [-1..+1]
const bodyBias = div(body,          add(rng, series_of(1e-9)));  // [-1..+1]
const asymRaw  = add(mult(series_of(0.6), wickBias), mult(series_of(0.4), bodyBias));
const asymZ    = zscore(asymRaw, zLen);

// 2) Efficiency
const effBar = div(absS(body), add(rng, series_of(1e-9)));       // [0..1]
const effZ   = zscore(effBar, zLen);

// 3) Trend tilt
const emaF  = ema(close, fastLen);
const emaS  = ema(close, slowLen);
const tiltR = div(sub(emaF, emaS), add(atrV, series_of(1e-9)));
const tiltZ = zscore(tiltR, zLen);

// 4) Energy (RMS body, signed)
const bodyRMS = sqrtS( ema( mult(body, body), 10 ) );
const energyR = div(bodyRMS, add(atrV, series_of(1e-9)));
const signedE = mult( energyR, for_every(body, b => (b==null?null:(b>=0?1:-1))) );
const energyZ = zscore(signedE, zLen);

// Composite weights
const wA = series_of(0.20), wE = series_of(0.25), wT = series_of(0.35), wN = series_of(0.20);
const compZ = add( add(mult(asymZ,wA), mult(effZ,wE)), add(mult(tiltZ,wT), mult(energyZ,wN)) );
const score = to100(compZ);  // 0..100

// ===== Guides (subtle bands to look different than MEC) =====
guide(35, 'Guide: 35');
guide(50, 'Guide: 50');
guide(65, 'Guide: 65');

// ===== Distinct score plot =====
if (scoreAsLine) {
  const colLine = for_every(score, s => (s==null)?null:(s>=65?cUp:(s<=35?cDn:cMid)));
  paint(score, { name:'AERIS score (line)', style:'line', thickness: lineWidth, color: colLine });
} else {
  const colHist = for_every(score, s => (s==null)?null:(s>=65?cUp:(s<=35?cDn:cMid)));
  paint(score, { name:'AERIS score (hist)', style:'column', color: colHist });
}

// ===== Optional parts (off by default) =====
if (showParts) {
  paint(to100(asymZ),   { name:'Asym 0..100',  style:'line', color:cA, thickness:2 });
  paint(to100(effZ),    { name:'Eff  0..100',  style:'line', color:cE, thickness:2 });
  paint(to100(tiltZ),   { name:'Tilt 0..100',  style:'line', color:cT, thickness:2 });
  paint(to100(energyZ), { name:'Ener 0..100',  style:'line', color:cN, thickness:2 });
}

// ===== Signals (same behaviour; names unchanged) =====
const wasBelowLong  = ema(for_every(score, s => (s!=null && s<thLong)?1:0), 2);
const wasAboveShort = ema(for_every(score, s => (s!=null && s>thShort)?1:0), 2);
register_signal( for_every(score, wasBelowLong,  (s,w)=> (w!=null&&w>0.5)&&(s!=null&&s>=thLong)), 'AERIS LONG');
register_signal( for_every(score, wasAboveShort, (s,w)=> (w!=null&&w>0.5)&&(s!=null&&s<=thShort)),'AERIS SHORT');

// Context (unchanged)
register_signal( for_every(to100(tiltZ),  t => t!=null && t>=60), 'AERIS TILT STRONG');
register_signal( for_every(to100(effZ),   e => e!=null && e>=60), 'AERIS EFF STRAIGHT');
register_signal( for_every(to100(asymZ),  a => a!=null && a>=60), 'AERIS ASYM BUY');
register_signal( for_every(to100(energyZ),n => n!=null && n>=60), 'AERIS ENERGY BUY');
register_signal( for_every(to100(tiltZ),  t => t!=null && t<=40), 'AERIS TILT WEAK');
register_signal( for_every(to100(effZ),   e => e!=null && e<=40), 'AERIS EFF CHOP');
register_signal( for_every(to100(asymZ),  a => a!=null && a<=40), 'AERIS ASYM SELL');
register_signal( for_every(to100(energyZ),n => n!=null && n<=40), 'AERIS ENERGY SELL');
</code>