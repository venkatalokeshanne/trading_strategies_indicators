<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Liquidity Map AVWAP #TSBuild25', 'price', {
  shortName: 'LM-AVWAP',
  decimals: 2
});

/* =============== Inputs =============== */
const lbL   = input.number('Pivot Left',  5);
const lbR   = input.number('Pivot Right', 5);
const nHigh = input.number('Last N High Pivots', 2);
const nLow  = input.number('Last N Low Pivots',  2);
const proxatrr = input.number('Proximity (× atrr)', 0.5);
const lenatrr  = input.number('atrr Len', 14);

/* =============== Helpers =============== */
function move(s,k){ const o=series_of(null); for(let i=0;i<s.length;i++){ const j=i-k; o[i]=(j>=0? s[j]:null);} return o; }

function is_pivot_high(i,L,R){ if (i-L<0||i+R>=time.length) return false;
  const v=high[i]; if(v==null) return false;
  for(let k=i-L;k<=i+R;k++){ if(high[k]!=null && high[k]>v) return false; }
  return true;
}
function is_pivot_low(i,L,R){ if (i-L<0||i+R>=time.length) return false;
  const v=low[i]; if(v==null) return false;
  for(let k=i-L;k<=i+R;k++){ if(low[k]!=null && low[k]<v) return false; }
  return true;
}

const prevClose = move(close,1);
const tr = for_every(high, low, prevClose, (h,l,pc)=> {
  if(h==null||l==null||pc==null) return null;
  return Math.max(Math.abs(h-l), Math.abs(h-pc), Math.abs(l-pc));
});
const atrr = ema(tr, lenatrr);

function avwap_from_anchor(idx){
  const out=series_of(null); let num=0,den=0;
  for(let i=idx;i<time.length;i++){
    if(close[i]!=null&&volume[i]!=null){ num+=close[i]*volume[i]; den+=volume[i]; out[i]=num/den; }
    else out[i]=(i>idx? out[i-1]: null);
  }
  return out;
}

/* Anchors */
let hiIdx=[], loIdx=[];
for(let i=0;i<time.length;i++){ if(is_pivot_high(i,lbL,lbR)) hiIdx.push(i); if(is_pivot_low(i,lbL,lbR)) loIdx.push(i); }
hiIdx=hiIdx.slice(-nHigh); loIdx=loIdx.slice(-nLow);

/* Paint + signals */
let proxTouch=series_of(false);
for(const idx of [...hiIdx,...loIdx]){
  const av=avwap_from_anchor(idx);
  paint(av,{color:'#4DA3FF',style:'line'});
  const up=for_every(av,atrr,(v,a)=>v!=null&&a!=null? v+a*proxatrr:null);
  const dn=for_every(av,atrr,(v,a)=>v!=null&&a!=null? v-a*proxatrr:null);
  paint(up,{color:'#999',style:'dotted'}); paint(dn,{color:'#999',style:'dotted'});
  const touch=for_every(close,up,dn,(c,u,l)=>c!=null&&u!=null&&l!=null&&(c<=u&&c>=l));
  proxTouch=for_every(proxTouch,touch,(a,b)=>a||b);
}

/* Signals */
register_signal(proxTouch,'LM: In AVWAP Zone');
</code>