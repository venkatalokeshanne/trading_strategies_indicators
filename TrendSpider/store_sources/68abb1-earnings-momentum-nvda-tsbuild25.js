<code x-ref="code" class="hljs" data-clipboard-text>// Earnings + Momentum (NVDA) — #TSBuild25
describe_indicator('Earnings + Momentum (NVDA) — #TSBuild25');

/* CSV: date,gap_pct,drift5_pct,label */
const CSV_DATA = `
date,gap_pct,drift5_pct,label
2025-04-27,6.4,9.1,E 0.76
2025-01-26,-2.7,1.2,E
2024-07-28,4.2,7.6,E 0.67
2024-04-28,8.9,15.3,E 5.98
2024-01-28,7.1,10.4,E 4.92
`.trim();

/* Inputs */
const TopK     = input.number('Top K markers', 5, { min:1, max:12 });
const RocLen   = input.number('ROC len',      10, { min:2, max:200 });
const EmaLen   = input.number('EMA len',      20, { min:5, max:200 });
const PressLen = input.number('Press len',    10, { min:2, max:200 });
const NormLen  = input.number('Norm len',     50, { min:5, max:300 });
const CalcSm   = input.number('Calc smooth',   3, { min:0, max:20  });
const ViewSm   = input.number('View smooth',   8, { min:0, max:30  });
const Cap      = input.number('Clip |Z|',      3, { min:1, max:10  });
const Wroc     = input.number('W ROC',       1.0, { min:0, max:3, step:0.1 });
const Wslope   = input.number('W Slope',     1.0, { min:0, max:3, step:0.1 });
const Wpress   = input.number('W Press',     1.0, { min:0, max:3, step:0.1 });

/* Helpers */
const EPS=1e-9;
function splitCSV(s){var o=[],c='',q=false;for(var i=0;i<s.length;i++){var ch=s[i];if(q){if(ch=='"'){if(i+1<s.length&&s[i+1]=='"'){c+='"';i++;}else q=false;}else c+=ch;}else{if(ch=='"')q=true;else if(ch==','){o.push(c);c='';}else c+=ch;}}o.push(c);return o;}
function iso(d){return d&&d.length===10&&d[4]==='-'&&d[7]==='-';}
function pct(x){var n=parseFloat(x);return isNaN(n)?'':(Math.round(n*100)/100).toFixed(2)+'%';}
function arrow(v){var n=parseFloat(v);if(isNaN(n)||n===0)return '•';return n>0?'▲':'▼';}
function col(v){var n=parseFloat(v);return isNaN(n)?'#cfcfcf':(n>=0?'#4cc38a':'#e25555');}
function abs_s(x){return for_every(x,v=>v<0?-v:v);}
function clip_s(x,c){return for_every(x,v=>v>c?c:(v<-c?-c:v));}
function norm_z(x,len){const d=ema(abs_s(x),len);return for_every(x,d,(a,den)=>a/((den&&den!==0)?den:EPS));}
function delta(s){let p=null;return for_every(s,v=>{var d=(p===null)?0:(v-p);p=v;return d;});}
function rocN(s,n){let b=[];return for_every(s,v=>{if(b.length<n){b.push(v);return 0;}const base=b[0]||v;b.push(v);b.shift();return (v-base)/((base!==0)?base:EPS);});}

/* Parse CSV → Top-K */
function eventsFromCSV(csv){
  var out=[], r=csv.split('n'); if(r.length<2) return out;
  var st=0, h=(r[0]||'').trim().toLowerCase(); if(h.indexOf('date')!==-1) st=1;
  for(var i=st;i<r.length;i++){
    var rowStr=(r[i]||'').trim(); if(!rowStr||rowStr==='...') continue;
    var p=splitCSV(rowStr); var d=(p[0]||'').trim(); if(!iso(d)) continue;
    var g=(p[1]||'').trim(), f=(p[2]||'').trim(), L=(p[3]||'').trim(); if(!L) L='E';
    var score=0.7*Math.abs(parseFloat(g)||0)+0.3*Math.abs(parseFloat(f)||0);
    out.push({d:d,g:g,f:f,l:L,s:score});
  }
  out.sort(function(a,b){return b.s-a.s;}); if(out.length>TopK) out=out.slice(0,TopK);
  out.sort(function(a,b){return (a.d<b.d)?1:((a.d>b.d)?-1:0);}); return out;
}
var EV=eventsFromCSV(CSV_DATA);

/* Momentum (lower pane, 0..100) */
const zRoc   = norm_z(rocN(close,RocLen), NormLen);
const emaC   = ema(close,EmaLen);
const zSlope = norm_z(for_every(delta(emaC),close,(d,c)=>d/((c&&c!==0)?c:EPS)), NormLen);
const vw     = vwap();
const zPress = norm_z(ema(for_every(close,vw,(c,v)=>(c-(v||1))/(v||1)), PressLen), NormLen);
const zRaw   = for_every(zRoc,zSlope,zPress,(r,s,p)=>Wroc*r+Wslope*s+Wpress*p);
const zClip  = clip_s((CalcSm>0?ema(zRaw,CalcSm):zRaw), Cap);
const osc    = for_every(zClip,v=>{var x=v/Cap;if(x>1)x=1;if(x<-1)x=-1;return (x+1)*50;});
const oscLine= (ViewSm>0)?ema(osc,ViewSm):osc;

/* guides */
const g50=for_every(close,_=>50), g60=for_every(close,_=>60), g40=for_every(close,_=>40);

/* plots */
plot(g50,{name:'EM_base50',color:'#666'});
plot(g60,{name:'EM_upper', color:'#3f63cc'});
plot(g40,{name:'EM_lower', color:'#b94b4b'});
plot(oscLine,{name:'EM',color:'#dddddd'});

/* On-chart markers */
function mark(d, txt, c, top){
  var ok=false;
  try{ if(draw&&draw.vline){ draw.vline(d,{color:c,width:1,style:'dashed'}); ok=true; } }catch(e){}
  try{ if(draw&&draw.label){ draw.label(d, close, txt, { color:c, valign:(top?'top':'bottom') }); ok=true; } }catch(e){}
  return ok;
}
for(var i=0;i<EV.length;i++){
  var e=EV[i], lbl = arrow(e.g)+' '+pct(e.g)+'/'+pct(e.f);
  mark(e.d, lbl, col(e.g), (i%2===0));
}

</code>