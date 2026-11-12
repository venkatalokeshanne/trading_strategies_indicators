<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('MTF Compass Pro #TSBuild25', 'price', {
  shortName: 'MTF Compass+',
  decimals: 2
});

/* =============== Inputs =============== */
const grpTF   = '① Horizons';
const grpCore = '② Core';
const grpThr  = '③ Thresholds';
const grpVis  = '④ Display';

const lenS  = input.number('Short EMA Len', 20, { min: 2, step: 1, group: grpTF });
const lenM  = input.number('Mid EMA Len',   50, { min: 3, step: 1, group: grpTF });
const lenL  = input.number('Long EMA Len', 200, { min: 5, step: 1, group: grpTF });

const rsiLen = input.number('RSI Len', 14, { min: 2, step: 1, group: grpCore });

const slopeK   = input.number('Min EMA Slope (× ATR%)', 0.1, { step: 0.01, group: grpThr });
const rsiBull  = input.number('RSI Bull ≥', 55, { min: 0, max: 100, step: 1, group: grpThr });
const rsiBear  = input.number('RSI Bear ≤', 45, { min: 0, max: 100, step: 1, group: grpThr });

const showOverlay = input.boolean('Show Compass Overlay', true, { group: grpVis });
const showSignals = input.boolean('Register Bias Signals', true, { group: grpVis });
const tintChart   = input.boolean('Background tint when aligned', true, { group: grpVis });

/* =============== Helpers =============== */
function move(s,k){ const o=series_of(null); for(let i=0;i<s.length;i++){ const j=i-k; o[i]=(j>=0? s[j]: null);} return o; }
function lastVal(s){ return s[s.length-1]; }
function fmt(x,dec=2){ return (x==null? '—' : Number(x).toFixed(dec)); }
function lerp(a,b,t){ return a+(b-a)*t; }
function colorBlend(c1,c2,t){ 
  const h1=parseInt(c1.slice(1),16), h2=parseInt(c2.slice(1),16);
  const r1=(h1>>16)&255,g1=(h1>>8)&255,b1=h1&255;
  const r2=(h2>>16)&255,g2=(h2>>8)&255,b2=h2&255;
  const r=lerp(r1,r2,t), g=lerp(g1,g2,t), b=lerp(b1,b2,t);
  return `#${Math.round(r).toString(16).padStart(2,'0')}${Math.round(g).toString(16).padStart(2,'0')}${Math.round(b).toString(16).padStart(2,'0')}`.toUpperCase();
}

/* TR & ATR% */
const prevClose = move(close,1);
const tr = for_every(high, low, prevClose, (h,l,pc)=>{
  if(h==null||l==null||pc==null) return null;
  return Math.max(Math.abs(h-l), Math.abs(h-pc), Math.abs(l-pc));
});
const atrCalc = ema(tr, 14);
const atrPct  = for_every(atrCalc, close, (a,c)=> (a!=null&&c!=null&&c!==0)? (100*a/c): null);

/* RSI */
const chg = for_every(close, prevClose, (c,p)=> (c!=null&&p!=null)? c-p: null);
const up  = for_every(chg, x=> (x!=null && x>0)? x: 0);
const dn  = for_every(chg, x=> (x!=null && x<0)? -x: 0);
const rUp = ema(up, rsiLen);
const rDn = ema(dn, rsiLen);
const rsi_indicator = for_every(rUp, rDn, (u,d)=> (u!=null && d!=null && (u+d)>0)? 100*u/(u+d): null);

/* EMAs & slopes */
const emaS = ema(close, lenS);
const emaM = ema(close, lenM);
const emaL = ema(close, lenL);

function normSlope(s){
  const d = for_every(s, move(s,1), (c,p)=> (c!=null&&p!=null)? c-p: null);
  return for_every(d, atrPct, (x,a)=> (x!=null&&a!=null&&a!==0)? (100*x/a): null);
}

const slS = normSlope(emaS);
const slM = normSlope(emaM);
const slL = normSlope(emaL);

/* Horizon bias logic */
function horizonBias(ema, slopeSeries){
  return for_every(close, ema, slopeSeries, rsi_indicator, (c,e,sl,rs)=>{
    if(c==null||e==null||sl==null||rs==null) return null;
    const bull = (c>e) && (sl>=slopeK) && (rs>=rsiBull);
    const bear = (c<e) && (sl<=-slopeK) && (rs<=rsiBear);
    if(bull) return 1;
    if(bear) return -1;
    return 0;
  });
}

const biasS = horizonBias(emaS, slS);
const biasM = horizonBias(emaM, slM);
const biasL = horizonBias(emaL, slL);

/* Snap latest */
const snap = {
  price: lastVal(close), rsi: lastVal(rsi_indicator),
  emaS: lastVal(emaS), emaM: lastVal(emaM), emaL: lastVal(emaL),
  slS: lastVal(slS), slM: lastVal(slM), slL: lastVal(slL),
  bS: lastVal(biasS), bM: lastVal(biasM), bL: lastVal(biasL)
};

/* Heatmap color for bias strength */
function biasColor(b){
  if(b==null) return '#C6C5C5';
  if(b>0) return colorBlend('#C6C5C5','#17B26A',0.9);
  if(b<0) return colorBlend('#C6C5C5','#F04438',0.9);
  return '#C6C5C5';
}
function biasArrow(b){ return b>0?'↑':(b<0?'↓':'→'); }

/* Alignment checks */
const allBull = (snap.bS===1 && snap.bM===1 && snap.bL===1);
const allBear = (snap.bS===-1 && snap.bM===-1 && snap.bL===-1);
const align2  = (([snap.bS,snap.bM,snap.bL].filter(x=>x===1).length>=2) ||
                 ([snap.bS,snap.bM,snap.bL].filter(x=>x===-1).length>=2));

/* Trade mode suggestion */
let modeText='Neutral';
if(allBull) modeText='TREND MODE: Bull Breakouts';
else if(allBear) modeText='TREND MODE: Bear Breakdowns';
else if(align2) modeText='Trend Bias (≥2 aligned)';
else modeText='RANGE MODE: Fade Extremes';

/* =============== Overlay Panel =============== */
if(showOverlay){
  const rows = [
    { cells: [{ text: 'Multi-Timeframe Compass Pro', bold:true }]},
    { cells: [{ text: `Mode: ${modeText}`, bold:true, color: (allBull?'#17B26A':allBear?'#F04438':'#FFA500') }]},
    { cells: [{ text: `Price: ${fmt(snap.price)}   RSI: ${fmt(snap.rsi,1)}`, color:'var(--text-color)' }]},
    { cells: [
        { text: `Short (${lenS}) EMA ${fmt(snap.emaS)}  Sl:${fmt(snap.slS,2)}×`, color:biasColor(snap.bS)},
        { text: biasArrow(snap.bS), align:'right', color:biasColor(snap.bS)}
    ]},
    { cells: [
        { text: `Mid   (${lenM}) EMA ${fmt(snap.emaM)}  Sl:${fmt(snap.slM,2)}×`, color:biasColor(snap.bM)},
        { text: biasArrow(snap.bM), align:'right', color:biasColor(snap.bM)}
    ]},
    { cells: [
        { text: `Long  (${lenL}) EMA ${fmt(snap.emaL)}  Sl:${fmt(snap.slL,2)}×`, color:biasColor(snap.bL)},
        { text: biasArrow(snap.bL), align:'right', color:biasColor(snap.bL)}
    ]},
    { cells: [{ text: 'Trend Alignment Meter', bold:true }]},
    { cells: [
        { text:'S', color:biasColor(snap.bS), align:'center', padding:4 },
        { text:'M', color:biasColor(snap.bM), align:'center', padding:4 },
        { text:'L', color:biasColor(snap.bL), align:'center', padding:4 }
    ]}
  ];

  paint_overlay('MTF_CompassPro', { position:'top_right' }, {
    rows,
    border:'solid var(--border-color) 1px',
    padding:6
  });
}

/* =============== Signals =============== */
if(showSignals){
  const bullNow = for_every(biasS,biasM,biasL,(s,m,l)=> s===1&&m===1&&l===1);
  const bearNow = for_every(biasS,biasM,biasL,(s,m,l)=> s===-1&&m===-1&&l===-1);
  const align2Up= for_every(biasS,biasM,biasL,(s,m,l)=> (s===1)+(m===1)+(l===1)>=2);
  const align2Dn= for_every(biasS,biasM,biasL,(s,m,l)=> (s===-1)+(m===-1)+(l===-1)>=2);

  register_signal(bullNow,'MTF+: All Bull');
  register_signal(bearNow,'MTF+: All Bear');
  register_signal(align2Up,'MTF+: ≥2 Bull');
  register_signal(align2Dn,'MTF+: ≥2 Bear');
}

/* =============== Chart Tint (merged series) =============== */
if(tintChart){
  const tintSeries = for_every(biasS,biasM,biasL,(s,m,l)=>{
    if(s===1 && m===1 && l===1) return '#E6FFEA'; // green tint
    if(s===-1 && m===-1 && l===-1) return '#FFE6E6'; // red tint
    return null;
  });
  color_candles(tintSeries);
}
</code>