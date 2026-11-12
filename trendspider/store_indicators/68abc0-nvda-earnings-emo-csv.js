<code x-ref="code" class="hljs" data-clipboard-text>// NVDA Earnings + EMO (CSV) — Data Integration (#TSBuild25)
// Uses TWO embedded CSVs:
//  • Earnings CSV (date,type,eps,label) -> on-chart markers
//  • EMO CSV (date,emo,signal,label,...) -> lower-panel step oscillator
// No HTTP. No tables. No rectangles.

describe_indicator('NVDA Earnings + EMO (CSV) — #TSBuild25');

// ===== YOUR CSVs (embedded verbatim) =====
const CSV_EARNINGS = `
date,type,eps,label
2025-04-27,Earnings,0.76,Q1 2026: $0.76
2025-01-26,Earnings,,Q4 2025
2024-07-28,Earnings,0.67,Q2 2025: $0.67
2024-04-28,Earnings,5.98,Q1 2025: $5.98
2024-01-28,Earnings,4.92,Q4 2024: $4.92
2023-10-29,Earnings,3.71,Q3 2024: $3.71
2023-07-30,Earnings,2.48,Q2 2024: $2.48
2023-04-30,Earnings,0.82,Q1 2024: $0.82
2023-01-29,Earnings,0.5700000000000001,Q4 2023: $0.57
2022-10-30,Earnings,0.27,Q3 2023: $0.27
2022-07-31,Earnings,0.26,Q2 2023: $0.26
2022-05-01,Earnings,0.64,Q1 2023: $0.64
2022-01-30,Earnings,1.1800000000000002,Q4 2022: $1.18
2021-10-31,Earnings,0.97,Q3 2022: $0.97
2021-08-01,Earnings,0.94,Q2 2022: $0.94
...
2013-07-28,Earnings,0.16,Q2 2014: $0.16
2013-04-28,Earnings,0.13,Q1 2014: $0.13
2013-01-27,Earnings,0.28,Q4 2013: $0.28
2012-10-28,Earnings,0.33,Q3 2013: $0.33
2012-07-29,Earnings,0.19,Q2 2013: $0.19
2012-04-29,Earnings,0.1,Q1 2013: $0.10
2012-01-29,Earnings,0.19,Q4 2012: $0.19
2011-10-30,Earnings,0.29,Q3 2012: $0.29
2011-07-31,Earnings,0.25,Q2 2012: $0.25
2011-05-01,Earnings,0.22,Q1 2012: $0.22
2011-01-30,Earnings,0.29,Q4 2011: $0.29
2010-10-29,Earnings,0.15,Q3 2011: $0.15
2010-07-29,Earnings,-0.25,Q2 2011: $-0.25
2010-04-29,Earnings,0.23,Q1 2011: $0.23
`.trim();

const CSV_EMO = `
date,emo,signal,label,qoq_growth,yoy_growth,acceleration,consistency,eps
2025-04-27,30.45,BULLISH,EMO: 30.4 (BULLISH),13.43,0,102.23,10.2,0.76
2024-07-28,-69.34,BEARISH,EMO: -69.3 (BEARISH),-88.8,-72.98,-110.34,39.9,0.67
2024-04-28,100,BULLISH,EMO: 100 (BULLISH),21.54,629.27,-11.07,64.6,5.98
2024-01-28,100,BULLISH,EMO: 100 (BULLISH),32.61,763.16,-16.98,41.25,4.92
2023-10-29,100,BULLISH,EMO: 100 (BULLISH),49.6,1274.07,-152.84,22.04,3.71
2023-07-30,100,BULLISH,EMO: 100 (BULLISH),202.44,853.85,158.58,4.42,2.48
2023-04-30,10.61,NEUTRAL,EMO: 10.6 (NEUTRAL),43.86,28.12,-67.25,44.07,0.82
2023-01-29,44.66,BULLISH,EMO: 44.7 (BULLISH),111.11,-51.69,107.26,54.39,0.5700000000000001
2022-10-30,-4.54,NEUTRAL,EMO: -4.5 (NEUTRAL),3.85,-72.16,63.22,26.34,0.27
2022-07-31,-36.47,BEARISH,EMO: -36.5 (BEARISH),-59.38,-72.34,-13.61,47.28,0.26
2022-05-01,-44.48,BEARISH,EMO: -44.5 (BEARISH),-45.76,-78.88,-67.41,76.16,0.64
2022-01-30,-1.95,NEUTRAL,EMO: -2.0 (NEUTRAL),21.65,-48.92,18.46,34.27,1.1800000000000002
2021-10-31,6.31,NEUTRAL,EMO: 6.3 (NEUTRAL),3.19,-54.25,72.17,43.01,0.97
2021-08-01,-35.24,BEARISH,EMO: -35.2 (BEARISH),-68.98,-5.05,-100.15,58.71,0.94
2021-05-02,59.49,BULLISH,EMO: 59.5 (BULLISH),31.17,106.12,22.21,60.01,3.03
`.trim();
// ======================================

// ---- Controls (numbers only) ----
const TopK     = input.number('Most recent K earnings', 7,  { min:1, max:20 });
const LabelTop = input.number('Labels: 1 top / 0 alt',  1,  { min:0, max:1  });
const ViewSm   = input.number('EMO display smoothing',   5,  { min:0, max:30 });

// Cut old stuff so markers aren’t in 2011
const MIN_DATE = '2022-01-01';

// ---- Utils ----
const EPS=1e-9;
function isISO(d){ return d && d.length===10 && d[4]==='-' && d[7]==='-'; }
function splitCSVRow(s){ var o=[],c='',q=false; for(var i=0;i<s.length;i++){var ch=s[i];
  if(q){ if(ch=='"'){ if(i+1<s.length&&s[i+1]=='"'){c+='"';i++;} else q=false; } else c+=ch; }
  else { if(ch=='"')q=true; else if(ch===','){ o.push(c); c=''; } else c+=ch; } }
  o.push(c); return o;
}
function toFixedPct(x){ var n=parseFloat(x); if(isNaN(n)) return ''; var r=Math.round(n*100)/100; return r.toFixed(2)+'%'; }

// ---- Parse earnings ----
function parseE(csv){
  var out=[], rows=csv.split('n'); if(rows.length<2) return out;
  var start=0, hdr=(rows[0]||'').trim().toLowerCase(); if(hdr.indexOf('date')!==-1) start=1;
  for(var i=start;i<rows.length;i++){
    var r=(rows[i]||'').trim(); if(!r||r==='...') continue;
    var p=splitCSVRow(r);
    var d=(p[0]||'').trim(); if(!isISO(d) || d<MIN_DATE) continue;
    var typ=(p[1]||'').trim();
    var eps=(p[2]||'').trim();
    var L  =(p[3]||'').trim(); if(!L) L = typ || 'E';
    out.push({ d:d, eps:eps, label:L });
  }
  // newest first then take K
  out.sort(function(a,b){ return (a.d<b.d)?1:((a.d>b.d)?-1:0); });
  if(out.length>TopK) out=out.slice(0,TopK);
  return out;
}

// ---- Parse EMO ----
function parseEMO(csv){
  var out=[], rows=csv.split('n'); if(rows.length<2) return out;
  var start=0, hdr=(rows[0]||'').trim().toLowerCase(); if(hdr.indexOf('date')!==-1) start=1;
  for(var i=start;i<rows.length;i++){
    var r=(rows[i]||'').trim(); if(!r||r==='...') continue;
    var p=splitCSVRow(r);
    var d=(p[0]||'').trim(); if(!isISO(d) || d<MIN_DATE) continue;
    var emo=parseFloat((p[1]||'').trim());
    var sig=(p[2]||'').trim();
    var L  =(p[3]||'').trim();
    if(isNaN(emo)) continue;
    out.push({ d:d, emo:emo, sig:sig, label:L });
  }
  // ascending so we can step-carry forward
  out.sort(function(a,b){ return (a.d>b.d)?1:((a.d<b.d)?-1:0); });
  return out;
}

var E = parseE(CSV_EARNINGS);
var M = parseEMO(CSV_EMO);

// ---- Build per-bar EMO step series (carry last value) ----
// impulse = new value at event dates, else 0
var impulse = for_every(close, function(_c){ return 0; });
for (var i=0;i<M.length;i++){ (function(v){
  var sig = series_of(v.d);
  impulse = for_every(impulse, sig, function(acc, s){ return acc + (s ? v.emo : 0); });
})(M[i]); }

// carry-forward last non-zero impulse
var lastVal=null;
var emoStep = for_every(impulse, function(x){
  if(x && x!==0) lastVal = x;
  return (lastVal===null) ? 0 : lastVal;
});

// smooth & map to 0..100 (assumes roughly -100..100)
var emoLine = (ViewSm>0) ? ema(emoStep, ViewSm) : emoStep;
var osc = for_every(emoLine, function(v){
  var x=v; if(x>100) x=100; if(x<-100) x=-100;
  return (x + 100) * 0.5;
});

// guides + plot (lower pane)
var g50=for_every(close, function(){ return 50; });
var g60=for_every(close, function(){ return 60; });
var g40=for_every(close, function(){ return 40; });
plot(g50,{ name:'__emo50', color:'#666' });
plot(g60,{ name:'__emo60', color:'#3f63cc' });
plot(g40,{ name:'__emo40', color:'#b94b4b' });
plot(osc,{ name:'EMO', color:'#dddddd' });

// ---- On-chart earnings markers (compact) ----
for (var j=0;j<E.length;j++){
  var ev = E[j];
  try{ if(draw && draw.vline) draw.vline(ev.d, { color:'#909090', width:1, style:'dashed' }); }catch(_){}
  try{ if(draw && draw.label){
    var t = ev.eps ? ('EPS '+ev.eps) : ev.label;
    var topSide = (LabelTop===1) ? true : (j%2===0);
    draw.label(ev.d, close, t, { color:'#cfcfcf', valign: topSide ? 'top' : 'bottom' });
  } }catch(_){}
}
</code>