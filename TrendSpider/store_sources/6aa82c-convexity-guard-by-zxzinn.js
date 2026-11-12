<code x-ref="code" class="hljs" data-clipboard-text>// Public-safe prototype. No trade direction, sizing, or orders.
describe_indicator('Convexity Guard by zxzinn', 'price', { shortName: 'Convexity Guard', warmup: 120 });
const lookback = input.number('Lookback bars', 5, { min: 2, max: 30 });
const threshold = input.number('Event threshold %', 0.55, { min: 0.10, max: 5.00 });
const resetLevel = input.number('Reset threshold', 0.35, { min: 0.10, max: 0.90 });
const showLabels = input.select('Event labels', 'Yes', ['Yes', 'No']);
const maxSpread = input.number('Max leg spread %', 18, { min: 1, max: 100 });
const moment = library('moment-timezone');
const TZ = 'America/New_York';
const sessionVwap = series_of(null);
let day = null, pv = 0, vol = 0;
for (let i = 0; i < close.length; i++) {    
const stamp = moment(time[i] * 1000).tz(TZ);    
const key = stamp.format('YYYY-MM-DD');    
if (key !== day) { day = key; pv = 0; vol = 0; }    
const minute = stamp.hour() * 60 + stamp.minute();    
if (minute < 570 || minute >= 960) { sessionVwap[i] = null; continue; }    
const barVol = Number.isFinite(volume[i]) ? volume[i] : 0;    
pv += ((high[i] + low[i] + close[i]) / 3) * barVol; vol += barVol;    
sessionVwap[i] = vol > 0 ? pv / vol : null;
}
const prior = shift(close, lookback);
const move = for_every(close, prior, (c, p) => Number.isFinite(p) && p > 0 ? (c - p) / p : null);
const event = series_of(false), reset = series_of(false), labels = series_of(null);
for (let i = 0; i < close.length; i++) {    
const stamp = moment(time[i] * 1000).tz(TZ), h = stamp.hour(), m = stamp.minute();    
const inWindow = (h > 14 || (h === 14 && m >= 30)) && h < 16;    
event[i] = inWindow && Number.isFinite(move[i]) && Math.abs(move[i]) >= threshold / 100;    
if (event[i]) {        
const hi = Math.max(...high.slice(Math.max(0, i - lookback + 1), i + 1));        
const lo = Math.min(...low.slice(Math.max(0, i - lookback + 1), i + 1));        
const loc = hi > lo ? (close[i] - lo) / (hi - lo) : 0.5;        
reset[i] = (move[i] > 0 && loc <= 1 - resetLevel) || (move[i] < 0 && loc >= resetLevel);
    }    
labels[i] = showLabels === 'Yes' && event[i] ? (reset[i] ? 'VOL EVENT<br/>RESET' : 'VOL EVENT') : null;
}
paint(sessionVwap, { name: 'Session VWAP', color: '#9C7CFF', style: 'line', thickness: 1 });
paint(labels, { name: 'Vol event', style: 'labels_above', color: '#E8EEF8', backgroundColor: '#7C6CF2', backgroundBorderRadius: 5, fontSize: 7 });
register_signal(event, 'Research volatility');
register_signal(reset, 'Research range reset');
const num = value => { const n = Number(String(value == null ? '' : value).replace(/[$,%]/g, '').replace(/,/g, '')); return Number.isFinite(n) ? n : NaN; };
let opt = { ok: false, expiry: '—', strike: NaN, cb: NaN, ca: NaN, pb: NaN, pa: NaN, ratio: NaN, cSpread: NaN, pSpread: NaN, oiRatio: NaN };
try {    
const ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/134 Safari/537.36';    
const asset = current.assetType === 'etf' ? 'etf' : 'stocks';    
const url = 'https://api.nasdaq.com/api/quote/' + current.symbol + '/option-chain?assetclass=' + asset + '&limit=1000';    
const response = await request.http(url, 300, { 'user-agent': ua, accept: 'application/json' });    
const rows = response && response.data && response.data.table && response.data.table.rows;    
assert(Array.isArray(rows), 'Options unavailable');    
const valid = rows.filter(r => r.expiryDate && Number.isFinite(num(r.strike)));    
assert(valid.length > 0, 'No option rows');    
const expiry = valid[0].expiryDate, sameExpiry = valid.filter(r => r.expiryDate === expiry).sort((a, b) => num(a.strike) - num(b.strike)), spot = close[close.length - 1];    
const atm = sameExpiry.reduce((a, b) => Math.abs(num(b.strike) - spot) < Math.abs(num(a.strike) - spot) ? b : a, sameExpiry[0]);    
const cb = num(atm.c_Bid), ca = num(atm.c_Ask), pb = num(atm.p_Bid), pa = num(atm.p_Ask), cm = (cb + ca) / 2, pm = (pb + pa) / 2;    
const quoteOk = [cb, ca, pb, pa].every(Number.isFinite) && cb >= 0 && pb >= 0 && ca > 0 && pa > 0 && ca >= cb && pa >= pb;    
const atmIndex = sameExpiry.indexOf(atm), nearby = sameExpiry.slice(Math.max(0, atmIndex - 3), atmIndex + 4);    
const callOi = nearby.reduce((s, r) => s + (num(r.c_Openinterest) || 0), 0);    
const putOi = nearby.reduce((s, r) => s + (num(r.p_Openinterest) || 0), 0);    
opt = { ok: quoteOk, expiry, strike: num(atm.strike), cb, ca, pb, pa, ratio: (ca + pa) / spot,        
cSpread: cm > 0 ? (ca - cb) / cm : NaN, pSpread: pm > 0 ? (pa - pb) / pm : NaN, oiRatio: callOi > 0 ? putOi / callOi : NaN };
} catch (e) {}
const i = close.length - 1, stamp = moment(time[i] * 1000).tz(TZ);
const pct = v => Number.isFinite(v) ? (v * 100).toFixed(2) + '%' : '—';
const cell = (text, color = '#E8EEF8') => ({ text, color, padding: 7 });
const vwapDistance = Number.isFinite(sessionVwap[i]) ? (close[i] - sessionVwap[i]) / close[i] : NaN;
const spreadsPass = opt.ok && opt.cSpread <= maxSpread / 100 && opt.pSpread <= maxSpread / 100;
const status = !opt.ok ? 'OPTIONS DATA UNAVAILABLE' : spreadsPass ? 'RESEARCH ONLY · QUOTE AGE UNKNOWN' : 'WIDE MARKET · DO NOT EXECUTE';
paint_overlay('CGPanel', { position: 'top_right', offset_y: 18, order: 'above_all' }, {    
background: '#0B1220', border: '1px solid #26354D', rows: [
        { cells: [cell('CONVEXITY GUARD', '#44D7E8'), cell('zxzinn research', '#8EA0B8')] },
        { cells: [cell(reset[i] ? 'VOLATILITY RESET' : event[i] ? 'VOLATILITY EVENT' : 'NO EVENT', reset[i] ? '#9C7CFF' : event[i] ? '#FFBD59' : '#8EA0B8'), cell(stamp.format('HH:mm') + ' ET')] },
        { cells: [cell(lookback + '-bar move: ' + pct(move[i])), cell('VWAP distance: ' + pct(vwapDistance))] },
        { cells: [cell('ATM ' + (Number.isFinite(opt.strike) ? opt.strike : '—') + ' · ' + opt.expiry), cell('Ask premium/spot: ' + pct(opt.ratio), '#44D7E8')] },
        { cells: [cell('Call bid/ask ' + (Number.isFinite(opt.cb) ? opt.cb.toFixed(2) : '—') + ' × ' + (Number.isFinite(opt.ca) ? opt.ca.toFixed(2) : '—') + '<br/>spread ' + pct(opt.cSpread)), cell('Put bid/ask ' + (Number.isFinite(opt.pb) ? opt.pb.toFixed(2) : '—') + ' × ' + (Number.isFinite(opt.pa) ? opt.pa.toFixed(2) : '—') + '<br/>spread ' + pct(opt.pSpread))] },
        { cells: [cell('Nearby put/call OI: ' + (Number.isFinite(opt.oiRatio) ? opt.oiRatio.toFixed(2) : '—'), '#9C7CFF'), cell(reset[i] ? 'Range reset detected' : 'No range reset', reset[i] ? '#9C7CFF' : '#8EA0B8')] },
        { cells: [{ ...cell(status, spreadsPass ? '#FFBD59' : '#FF6577'), colspan: 2, textAlign: 'center' }] },
        { cells: [{ ...cell('Research only · no order instruction', '#8EA0B8'), colspan: 2, textAlign: 'center' }] }
    ]
});</code>