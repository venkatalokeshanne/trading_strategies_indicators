<code x-ref="code" class="hljs" data-clipboard-text>// RSI MTF Stack v0.5
// Multi-timeframe RSI table rendered on-chart.
//
// The row matching the chart resolution is computed from native close[] and
// matches the built-in RSI exactly. Other rows are fetched; request.history()
// returns CLOSED bars only, so the current close is appended as the forming bar
// before the RSI is taken. Those rows track a native read within ~0.1.

describe_indicator('RSI MTF Stack', { shortName: '📊 RSI MTF' });

const moment = library('moment-timezone');

const TF_LIST = ['1', '2', '3', '5', '10', '15', '30', '60', '120', '240', 'D', 'W', 'M'];

const TF_LABEL = {
  '1': '1 min',   '2': '2 min',   '3': '3 min',   '5': '5 min',
  '10': '10 min', '15': '15 min', '30': '30 min', '60': '1 hour',
  '120': '2 hour', '240': '4 hour',
  'D': 'Daily',   'W': 'Weekly',  'M': 'Monthly'
};

function tfLabel(tf) { return TF_LABEL[tf] || String(tf); }

const tf1 = input.select('Timeframe 1', '15', TF_LIST);
const tf2 = input.select('Timeframe 2', '60', TF_LIST);
const tf3 = input.select('Timeframe 3', 'D', TF_LIST);

const rsiLength = input.number('RSI Length', 14, { min: 1, max: 100 });
const obLevel   = input.number('Overbought Level', 70, { min: 51, max: 100 });
const bullLevel = input.number('Bullish Above',    55, { min: 51, max: 99 });
const bearLevel = input.number('Bearish Below',    45, { min: 1,  max: 49 });
const osLevel   = input.number('Oversold Level',   30, { min: 0,  max: 49 });
const useTiers  = input.boolean('Overbought/Oversold Colors', true);

const levelsOk =
  Number.isFinite(osLevel) && Number.isFinite(bearLevel) &&
  Number.isFinite(bullLevel) && Number.isFinite(obLevel) &&
  (osLevel < bearLevel) && (bearLevel < bullLevel) && (bullLevel < obLevel);

const LV = levelsOk
  ? { os: osLevel, bear: bearLevel, bull: bullLevel, ob: obLevel }
  : { os: 30, bear: 45, bull: 55, ob: 70 };

const scaleChoice    = input.select('UI Scale', '100%', ['65%','80%', '100%', '120%', '150%']);
const showTable  = input.boolean('Show Table', true);
const showStatus = input.boolean('Show Status Dot', true);
const showFooter = input.boolean('Show Status Footer', true);

const uiScale = parseInt(scaleChoice, 10);
function scaleVal(n) { return Math.max(1, Math.round(n * uiScale / 100)); }
function px(n) { return scaleVal(n) + 'px'; }
function pad(v, h) { return px(v) + ' ' + px(h); }

const fs = { hdr: 13, row: 12, foot: 10 };

const TH = {
  panelBg: 'rgba(0, 0, 0, 0.7)',
  titleBg: '#222222',
  labelBg: 'rgba(42, 53, 59, 0.9)',
  footBg:  'rgba(20, 26, 30, 0.95)',
  bullBg:  'rgba(0, 150, 0, 0.8)',
  bearBg:  'rgba(220, 20, 20, 0.8)',
  obBg:    '#79FF3B',
  osBg:    '#F608FD',
  neutBg:  '#8A6D1F',
  flatBg:  'rgba(128, 128, 128, 0.7)',
  text:    'white',
  footFg:  '#9FB6C9',
  border:  '#444444'
};

function toMs(ts) {
  if (ts === null || ts === undefined) return null;
  return ts < 1e12 ? ts * 1000 : ts;
}

function lastFinite(series) {
  if (!series || !series.length) return null;
  for (let i = series.length - 1; i >= 0; i--) {
    if (Number.isFinite(series[i])) return series[i];
  }
  return null;
}

const chartRes    = String(current.resolution);
const chartLastMs = toMs(time[time.length - 1]);
const curClose    = close[close.length - 1];

const seriesCache = {};

async function readTimeframe(tf) {
  const key = String(tf);
  if (seriesCache[key] !== undefined) return seriesCache[key];

  let result = { value: null, source: 'err', filled: false };

  if (key === chartRes) {
    result = { value: lastFinite(rsi(close, rsiLength)), source: 'native', filled: false };
  } else {
    try {
      const data = await request.history(current.ticker, key);
      if (data && data.close && data.close.length) {
        let closes = data.close;
        let filled = false;

        const fetchLastMs = (data.time && data.time.length)
          ? toMs(data.time[data.time.length - 1])
          : null;

        const chartLeads = (chartLastMs !== null && fetchLastMs !== null && chartLastMs > fetchLastMs);

        if (chartLeads && Number.isFinite(curClose)) {
          closes = data.close.concat([curClose]);
          filled = true;
        }

        result = { value: lastFinite(rsi(closes, rsiLength)), source: 'fetch', filled: filled };
      }
    } catch (e) {
      result = { value: null, source: 'err', filled: false };
    }
  }

  seriesCache[key] = result;
  return result;
}

const r1 = await readTimeframe(tf1);
const r2 = await readTimeframe(tf2);
const r3 = await readTimeframe(tf3);

function isOk(v) { return Number.isFinite(v); }

function resolveTier(v) {
  if (!isOk(v)) return 'na';
  if (useTiers && v >= LV.ob)   return 'ob';
  if (useTiers && v <= LV.os)   return 'os';
  if (v >= LV.bull)             return 'bull';
  if (v <= LV.bear)             return 'bear';
  return 'neutral';
}

const TIER_BG = {
  ob: TH.obBg, bull: TH.bullBg, neutral: TH.neutBg,
  bear: TH.bearBg, os: TH.osBg, na: TH.flatBg
};

const TIER_DOT = {
  ob: '🟢 ', bull: '🟢 ', neutral: '⚪ ',
  bear: '🔴 ', os: '🔴 ', na: '⚫ '
};

function statusDot(tier) {
  if (!showStatus) return '';
  return TIER_DOT[tier] || '⚫ ';
}

function valueBg(tier) {
  return TIER_BG[tier] || TH.flatBg;
}

function hexLuminance(hex) {
  if (typeof hex !== 'string') return null;
  let h = hex.trim();
  if (h.charAt(0) !== '#') return null;
  h = h.slice(1);
  if (h.length === 3) h = h.charAt(0) + h.charAt(0) + h.charAt(1) + h.charAt(1) + h.charAt(2) + h.charAt(2);
  if (h.length !== 6) return null;

  const chan = [];
  for (let i = 0; i < 3; i++) {
    const n = parseInt(h.substr(i * 2, 2), 16);
    if (!Number.isFinite(n)) return null;
    const x = n / 255;
    chan.push(x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4));
  }
  return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2];
}

function pickTextColor(bg) {
  const L = hexLuminance(bg);
  if (L === null) return TH.text;
  const vsWhite = (1.05) / (L + 0.05);
  const vsBlack = (L + 0.05) / 0.05;
  return vsBlack > vsWhite ? '#000000' : '#FFFFFF';
}

function valueText(v) { return isOk(v) ? v.toFixed(2) : 'N/A'; }

function buildRow(tf, res) {
  const v = res ? res.value : null;
  const tier = resolveTier(v);
  const bg = valueBg(tier);
  const fg = pickTextColor(bg);
  return {
    cells: [
      {
        text: tfLabel(tf),
        color: TH.text,
        background: TH.labelBg,
        padding: pad(4, 8),
        fontSize: px(fs.row),
        fontWeight: 'bold',
        textAlign: 'left'
      },
      {
        text: statusDot(tier) + valueText(v),
        color: fg,
        background: bg,
        padding: pad(4, 8),
        fontSize: px(fs.row),
        fontWeight: 'bold',
        textAlign: 'right'
      }
    ]
  };
}

const isDailyRes = (chartRes === 'D' || chartRes === 'W' || chartRes === 'M');

function buildFooterText() {
  let stamp;
  if (chartLastMs === null) {
    stamp = isDailyRes ? '--/--' : '--:-- ET';
  } else if (isDailyRes) {
    stamp = moment(chartLastMs).tz('America/New_York').format('MM/DD');
  } else {
    stamp = moment(chartLastMs).tz('America/New_York').format('HH:mm') + ' ET';
  }

  const nativeTfs = [];
  const filledTfs = [];
  const pairs = [[tf1, r1], [tf2, r2], [tf3, r3]];

  for (let i = 0; i < pairs.length; i++) {
    const tf = pairs[i][0], res = pairs[i][1];
    if (!res) continue;
    if (res.source === 'native' && nativeTfs.indexOf(tf) < 0) nativeTfs.push(tf);
    if (res.filled && filledTfs.indexOf(tf) < 0) filledTfs.push(tf);
  }

  const isLive = (filledTfs.length > 0 || nativeTfs.length > 0);
  let txt = stamp + ' · ' + (isLive ? 'live' : 'closed');
  if (nativeTfs.length) txt += ' · exact: ' + nativeTfs.map(tfLabel).join(',');
  return txt;
}

const visibleRows = [
  {
    cells: [{
      text: 'MTF RSI (' + rsiLength + ')',
      colspan: 2,
      color: TH.text,
      background: TH.titleBg,
      padding: pad(6, 10),
      fontSize: px(fs.hdr),
      fontWeight: 'bold',
      textAlign: 'center'
    }]
  },
  buildRow(tf1, r1),
  buildRow(tf2, r2),
  buildRow(tf3, r3)
];

if (showFooter) {
  visibleRows.push({
    cells: [{
      text: buildFooterText(),
      colspan: 2,
      color: TH.footFg,
      background: TH.footBg,
      padding: pad(2, 8),
      fontSize: px(fs.foot),
      fontWeight: 'normal',
      textAlign: 'center'
    }]
  });
}

const hiddenRows = [
  { cells: [{ text: '', color: 'transparent', background: 'transparent', padding: '0px' }] }
];


paint_overlay(
  'RSI MTF Stack',
  {
    order: 'above_all',
    offset_x: 0,
    offset_y: 0
  },
  showTable
    ? {
        fontSize: scaleVal(fs.row),
        background: TH.panelBg,
        border: scaleVal(1) + 'px solid ' + TH.border,
        borderRadius: px(6),
        rows: visibleRows
      }
    : {
        fontSize: 1,
        background: 'transparent',
        border: 'none',
        rows: hiddenRows
      }
);</code>