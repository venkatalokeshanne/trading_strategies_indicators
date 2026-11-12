<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Options Gravity Map (Pin Risk + Magneto-Flow) #TSBuild25', 'price', {
  shortName: 'OptGravity',
  decimals: 2
});

/* =============== Inputs =============== */
const gSrc  = '① Source & Filters';
const gBand = '② Band/Potential';
const gVis  = '③ Visuals';
const gSig  = '④ Signals';

const srcMode     = input.select('Source', 'Options', ['Options','Grid','Manual'], { group: gSrc });
const topN        = input.number('Top N strikes (by size)', 5, { min: 1, max: 15, step: 1, group: gSrc });
const minSize     = input.number('Min option size', 1, { min: 1, step: 1, group: gSrc });
const useCALL     = input.boolean('Include CALL', true,  { group: gSrc });
const usePUT      = input.boolean('Include PUT',  true,  { group: gSrc });

/* Manual (few fields, numeric defaults) */
const mCount = input.number('Manual: count (0–4)', 0, { min: 0, max: 4, step: 1, group: gSrc });
const ms1 = input.number('S1', 0, { group: gSrc });
const ms2 = input.number('S2', 0, { group: gSrc });
const ms3 = input.number('S3', 0, { group: gSrc });
const ms4 = input.number('S4', 0, { group: gSrc });

/* Band/Potential parameters */
const bandMode   = input.select('Band width mode', 'Absolute', ['Absolute','ATR ×'], { group: gBand });
const bandAbs    = input.number('Band ±Abs', 2.0, { min: 0.05, step: 0.05, group: gBand });
const atrLen     = input.number('ATR Len (if ATR ×)', 14, { min: 2, step: 1, group: gBand });
const bandATRx   = input.number('Band ATR ×', 0.5, { min: 0.05, step: 0.05, group: gBand });
const alpha      = input.number('Gravity falloff α', 1.5, { min: 0.5, step: 0.1, group: gBand }); // higher = shorter reach
const potScale   = input.number('Potential scale (0–100≈max)', 100, { min: 10, step: 5, group: gBand });

/* Visuals */
const showWalls   = input.boolean('Show top-N walls', true, { group: gVis });
const tintPins    = input.boolean('Tint candles when pin risk high', true, { group: gVis });
const showBary    = input.boolean('Show options barycenter line', true, { group: gVis });
const showMagnet  = input.boolean('Show Magnet label', true, { group: gVis });
const showDots    = input.boolean('Show dots when inside any band', false, { group: gVis });

/* Signals */
const pinZ        = input.number('Pin Risk threshold (0–100)', 60, { min: 1, max: 100, step: 1, group: gSig });
const flowThr     = input.number('Flow threshold (|value|)', 10, { min: 1, step: 1, group: gSig });
const nearMagAbs  = input.number('Near-Magnet distance (abs)', 1.0, { min: 0.01, step: 0.01, group: gSig });

/* =============== Helpers =============== */
function move(s,k){ const o=series_of(null); for(let i=0;i<s.length;i++){ const j=i-k; o[i]=(j>=0? s[j]: null);} return o; }
const prevClose = move(close,1);
const tr = for_every(high, low, prevClose, (h,l,pc,i)=>{
  if (i===0) return null;
  const a=(h!=null&&l!=null)?Math.abs(h-l):null;
  const b=(h!=null&&pc!=null)?Math.abs(h-pc):null;
  const c=(l!=null&&pc!=null)?Math.abs(l-pc):null;
  const m=Math.max(a==null?-Infinity:a, b==null?-Infinity:b, c==null?-Infinity:c);
  return m===-Infinity? null: m;
});
const atrCalc = ema(tr, atrLen);
function bandWidthAt(i){
  if (bandMode==='ATR ×'){ const a=atrCalc[i]; return (a!=null? a*bandATRx: null); }
  return bandAbs;
}

/* =============== Build strikes from options (or fallback) =============== */
let strikes = [];      // numeric strikes
let sizes   = [];      // total size per strike
let calls   = [];      // call size per strike
let puts    = [];      // put size per strike
let infoTxt = '';
let usedOptions = false;

if (srcMode==='Options'){
  try{
    const opt = await request.unusual_options(current.ticker);
    if (opt && Array.isArray(opt) && opt.length>0){
      const agg = {}; // strike -> {total,calls,puts}
      for (let i=0;i<opt.length;i++){
        const o=opt[i]; if(!o) continue;
        const k=Number(o.strike); const t=o.type; const sz=Number(o.size);
        if(!isFinite(k)||!isFinite(sz)) continue;
        if(sz < minSize) continue;
        if((t==='CALL'&&!useCALL)||(t==='PUT'&&!usePUT)) continue;
        if(agg[k]==null) agg[k]={total:0,calls:0,puts:0};
        agg[k].total+=sz; if(t==='CALL') agg[k].calls+=sz; if(t==='PUT') agg[k].puts+=sz;
      }
      let rows=[];
      for (const ks in agg){ rows.push({k:Number(ks), t:agg[ks].total, c:agg[ks].calls, p:agg[ks].puts}); }
      rows.sort((a,b)=> b.t - a.t);
      const take=Math.min(topN, rows.length);
      for (let i=0;i<take;i++){ strikes.push(rows[i].k); sizes.push(rows[i].t); calls.push(rows[i].c); puts.push(rows[i].p); }
      usedOptions = strikes.length>0;
      infoTxt = usedOptions? `Options walls (top ${take})` : 'No qualifying options — grid fallback';
    } else {
      infoTxt = 'No unusual options — grid fallback';
    }
  } catch(e){
    infoTxt = 'Options fetch error — grid fallback';
  }
}

if (!usedOptions && srcMode==='Manual'){
  const arr=[ms1,ms2,ms3,ms4]; const N=Math.min(mCount,arr.length);
  for(let i=0;i<N;i++){ const v=arr[i]; if(v!=null && isFinite(v) && v>0){ strikes.push(v); sizes.push(1); calls.push(0); puts.push(0);} }
  infoTxt = `Manual walls (${strikes.length})`;
}

if (strikes.length===0){
  // Grid: 3 nearest round-step
  const last=close[close.length-1];
  if(last!=null){
    const step=Math.max(0.0001, last*0.05); // 5% default
    const base=Math.round(last/step)*step;
    strikes=[base-step, base, base+step]; sizes=[1,1,1]; calls=[1,0,0]; puts=[0,1,1];
    infoTxt = (srcMode==='Grid')? 'Grid (3-nearest)' : (infoTxt || 'Fallback: Grid (3-nearest)');
  }
}

/* dedupe & sort keeping arrays aligned */
function sortByStrikes(){
  // simple insertion sort to keep arrays aligned
  for(let i=1;i<strikes.length;i++){
    let j=i; const sk=strikes[i], sz=sizes[i], ca=calls[i], pu=puts[i];
    while(j>0 && strikes[j-1]>sk){ strikes[j]=strikes[j-1]; sizes[j]=sizes[j-1]; calls[j]=calls[j-1]; puts[j]=puts[j-1]; j--; }
    strikes[j]=sk; sizes[j]=sz; calls[j]=ca; puts[j]=pu;
  }
}
sortByStrikes();

/* =============== Derived: barycenter & gravity field =============== */
// options barycenter (center of mass)
let totalSize=0, weighted=0;
for(let i=0;i<strikes.length;i++){ if(isFinite(sizes[i])){ totalSize+=sizes[i]; weighted+=strikes[i]*sizes[i]; } }
const bary = (totalSize>0)? (weighted/totalSize): null;

/* Gravity potential & gradient series
   potential(p) = Σ size / (1 + |p - k|/W)^α
   gradient(p)  = Σ size * sign(k - p) / (1 + |p - k|/W)^(α+1)
*/
const eps=1e-9;
const potential = for_every(close, (_c,_p,i)=>{
  const p=close[i]; if(p==null) return null;
  const W = bandWidthAt(i); if(W==null) return null;
  let total=0;
  for(let j=0;j<strikes.length;j++){
    const d=Math.abs(p - strikes[j])/(W+eps);
    total += sizes[j] / Math.pow(1 + d, alpha);
  }
  return (totalSize>0)? (total / totalSize) * potScale : null; // scaled 0..potScale
});

const flow = for_every(close, (_c,_p,i)=>{
  const p=close[i]; if(p==null) return null;
  const W=bandWidthAt(i); if(W==null) return null;
  let g=0;
  for(let j=0;j<strikes.length;j++){
    const s = (strikes[j] >= p)? 1 : -1;
    const d=Math.abs(p - strikes[j])/(W+eps);
    g += sizes[j] * s / Math.pow(1 + d, alpha+1);
  }
  // normalize by totalSize and scale approximately to ±potScale/2
  return (totalSize>0)? (g / totalSize) * (potScale/2) : null;
});

/* =============== Draw =============== */
// Walls with call/put dominance coloring
if (showWalls){
  for(let i=0;i<strikes.length;i++){
    const domCall = calls[i] >= puts[i];
    const col = domCall ? '#4DA3FF' : '#E05A5A';
    paint(horizontal_line(strikes[i]), { name: `Wall ${Number(strikes[i]).toFixed(2)}`, color: col, style: 'dotted' });

    // dynamic band per bar
    const up = for_every(close, (_c,_p,ii)=> { const w=bandWidthAt(ii); return (w==null? null: strikes[i] + w);} );
    const dn = for_every(close, (_c,_p,ii)=> { const w=bandWidthAt(ii); return (w==null? null: strikes[i] - w);} );
    paint(up, { name: '', color: col, style: 'dotted' });
    paint(dn, { name: '', color: col, style: 'dotted' });

    const inBand = for_every(close, up, dn, (c,u,d)=> (c!=null&&u!=null&&d!=null)? (c<=u && c>=d): false);
    if (showDots){ const dots=for_every(inBand, (b,ii)=> b? close[ii]: null); paint(dots, { name: '', color: '#FFB000', style: 'dots', thickness: 3 }); }
  }
}

// Barycenter
if (showBary && bary!=null){
  paint(horizontal_line(bary), { name: 'Barycenter', color: '#C0C0C0', style: 'line' });
}

/* Pin-risk tint */
if (tintPins){
  const tint = for_every(potential, v=>{
    if (v==null) return null;
    return (v >= pinZ) ? '#E9D7FF' : null; // light plum when high potential
  });
  color_candles(tint);
}

/* Magnet label (nearest strike to last bar) + info */
const lastC = close[close.length-1];
let bestLevel=null, bestDist=null;
if (lastC!=null && strikes.length>0){
  for(let i=0;i<strikes.length;i++){
    const d=Math.abs(lastC - strikes[i]);
    if(bestDist==null || d<bestDist){ bestDist=d; bestLevel=strikes[i]; }
  }
}
const magnetText = (bestLevel!=null && bestDist!=null)
  ? `Magnet ${bestLevel>lastC?'↑':(bestLevel<lastC?'↓':'•')} ${Number(bestLevel).toFixed(2)}  (Δ=${Number(bestDist).toFixed(2)})`
  : 'Magnet: n/a';

paint_overlay('magnet_overlay', { position: 'top_right' }, {
  rows: showMagnet
    ? [{ cells: [{ text: magnetText, color: 'var(--text-color)', padding: 6, border: 'solid var(--border-color) 1px' }]}]
    : []
});

/* =============== Signals =============== */
// 1) Pin risk high (potential ≥ pinZ)
const pinHigh = for_every(potential, v => (v!=null && v >= pinZ));
register_signal(pinHigh, 'OptGrav: Pin Risk High');

// 2) Magneto-flow direction
const upFlow   = for_every(flow, v => (v!=null && v >=  flowThr));
const downFlow = for_every(flow, v => (v!=null && v <= -flowThr));
register_signal(upFlow,   'OptGrav: Up-Flow (options pull up)');
register_signal(downFlow, 'OptGrav: Down-Flow (options pull down)');

// 3) Near magnet (distance to nearest wall ≤ threshold)
const nearMag = for_every(close, c=>{
  if(c==null || strikes.length===0) return false;
  let dmin=null;
  for(let i=0;i<strikes.length;i++){
    const d=Math.abs(c - strikes[i]); if(dmin==null || d<dmin) dmin=d;
  }
  return (dmin!=null && dmin <= nearMagAbs);
});
register_signal(nearMag, 'OptGrav: Near Magnet (≤ distance)');
</code>