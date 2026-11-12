<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Insider Trades', { shortName: '🐳 Insiders' });

// ─────────────────────────────────────────────────────────────────────────────
// Inputs
// ─────────────────────────────────────────────────────────────────────────────
const myLookbackDays = input.number('Lookback Period (Days)', 14, { min: 1 });
const myFontSize     = input.number('Font Size', 12, { min: 8, max: 30 });

// Section toggles
const showAwards = input.boolean('Show AWARD section', true);
const showOther  = input.boolean('Show OTHER section',  true);

// ─────────────────────────────────────────────────────────────────────────────
// Theme selector
// ─────────────────────────────────────────────────────────────────────────────
const themeName = input.select('Theme', 'Steel + Cyan', [
  'Midnight Neon',
  'Steel + Cyan',
  'Monochrome + Accent'
]);

function pickTheme(_name) {
  if (_name === 'Steel + Cyan') {
    return {
      panelBg: 'rgba(29, 41, 61, 0.85)',
      text: '#E5E7EB',
      mutedText: '#CBD5E1',
      headerBg: '#1D293D',
      headerText: '#E5E7EB',
      buy: '#00CBD6',
      sell: '#FB7185',
      award: '#D6C100',
      other: '#A3A3A3',
      border: '#22D3EE',
      divider: 'rgba(148, 163, 184, 0.35)',
      buyHeaderBg: '#0B1220',
      sellHeaderBg: '#0B1220',
      awardHeaderBg: '#0B1220',
      otherHeaderBg: '#0B1220',
      sectionHeaderText: '#E5E7EB'
    };
  }

  // Bloomberg-esque Monochrome + Accent
  if (_name === 'Monochrome + Accent') {
    return {
      panelBg: 'rgba(0, 0, 0, 0.92)',
      text: '#E5E5E5',
      mutedText: '#A3A3A3',

      headerBg: '#0A0A0A',
      headerText: '#FFB000',

      // Keep values monochrome; other slightly dimmer
      buy:  '#E5E5E5',
      sell: '#E5E5E5',
      award:'#E5E5E5',
      other:'#A3A3A3',

      border: 'rgba(255, 176, 0, 0.75)',
      divider: 'rgba(255, 255, 255, 0.10)',

      buyHeaderBg:   '#111111',
      sellHeaderBg:  '#111111',
      awardHeaderBg: '#111111',
      otherHeaderBg: '#111111',
      sectionHeaderText: '#FFB000'
    };
  }

  // Midnight Neon (default)
  return {
    panelBg: 'rgba(10, 12, 18, 0.88)',
    text: '#E5E7EB',
    mutedText: '#CBD5E1',
    headerBg: '#100099',
    headerText: '#FFFFFF',
    buy: '#22C55E',
    sell: '#EF4444',
    award: '#F59E0B',
    other: '#94A3B8',
    border: 'rgba(255, 255, 255, 0.750)',
    divider: 'rgba(148, 163, 184, 0.30)',
    buyHeaderBg: '#111827',
    sellHeaderBg: '#111827',
    awardHeaderBg: '#111827',
    otherHeaderBg: '#111827',
    sectionHeaderText: '#FFFFFF'
  };
}

const THEME = pickTheme(themeName);

// ─────────────────────────────────────────────────────────────────────────────
// Data fetch
// ─────────────────────────────────────────────────────────────────────────────
const myInsiderData = await request.insider_trading(current.ticker);
assert(!myInsiderData.error, `Error fetching insider trading data: ${myInsiderData.error}`);

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
const myFormatLargeNumber = (_value, _decimals = 0) =>
  isNaN(_value) ? '—' : Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: _decimals }).format(_value);

function myFormatDateFromTimestamp(_timestamp) {
  const tsNum  = parseInt(_timestamp);
  const ms     = (String(tsNum).length <= 10 ? tsNum * 1000 : tsNum);
  const moment = library('moment-timezone');
  return moment(ms).format('MM/DD/YYYY');
}

// Canonical grouping (raw data unchanged; we derive actionType for display only)
function myNormalizeAction(_transaction, _action) {
  const t = (_transaction || '').toLowerCase();
  const a = (_action || '').toLowerCase();
  if (t === 'buy')  return 'BUY';
  if (t === 'sell') return 'SELL';
  if (t === 'award' || a === 'award') return 'AWARD';
  return 'OTHER';
}

// Display action text:
// - BUY/SELL/AWARD show group label
// - OTHER shows the *raw* subtype (e.g., GIFT) WITHOUT changing grouping
function myDisplayActionText(t) {
  if (t.actionType !== 'OTHER') return t.actionType;
  const raw = (t.transaction || t.action || 'unknown').toUpperCase();
  return raw;
}

// Lookback cutoff
function myGetDaysAgoTimestamp(_days) {
  const secsInDay = 24 * 60 * 60;
  const nowTs     = time[time.length - 1];
  return nowTs - (_days * secsInDay);
}

const myLookbackTimestamp = myGetDaysAgoTimestamp(myLookbackDays);

// Normalize + collect transactions within lookback (raw fields preserved)
const myTransactions = (myInsiderData.transactions || [])
  .filter(t => t.timestamp >= myLookbackTimestamp)
  .map(t => {
    const info = myInsiderData.insidersByCIK?.[t.insider] || {};
    const own  = myInsiderData.ownershipByCIK?.[t.insider] || 0;
    return {
      // raw fields (unchanged)
      timestamp:   t.timestamp,
      transaction: t.transaction,
      action:      t.action,
      volume:      t.volume,
      netValue:    t.netValue,
      isGift:      t.isGift || false,
      // enrich
      owner_name:  info.name || 'Unknown',
      owner_title: info.role?.title || 'Unknown',
      total_owned: own,
      // derived grouping
      actionType:  myNormalizeAction(t.transaction, t.action)
    };
  })
  .sort((a, b) => b.timestamp - a.timestamp);

const hasAnyTransactions = myTransactions.length > 0;

// ─────────────────────────────────────────────────────────────────────────────
// Monospace-like alignment illusion:
// - right align numeric columns
// - padStart numeric strings to uniform widths (based on current dataset)
// ─────────────────────────────────────────────────────────────────────────────
let maxSharesLen = 1;
let maxValueLen  = 1;

for (const t of myTransactions) {
  const s = myFormatLargeNumber(t.volume);
  const v = '$' + myFormatLargeNumber(t.netValue);
  if (s && s.length > maxSharesLen) maxSharesLen = s.length;
  if (v && v.length > maxValueLen)  maxValueLen  = v.length;
}

function padNum(_txt, _len) {
  const s = String(_txt ?? '');
  return s.padStart(_len, ' ');
}

// ─────────────────────────────────────────────────────────────────────────────
// Tight spacing + alignment primitives
// ─────────────────────────────────────────────────────────────────────────────
const PAD_HEAD = '1px 6px';
const PAD_ROW  = '2px 6px';
const PAD_SEC  = '2px 6px';

// Base cells
const myHeadCell  = (_text, _align = 'left') => ({ text: `${_text}`, fontWeight: 'bold', color: THEME.headerText, padding: PAD_HEAD, textAlign: _align });
const myValueCell = (_text, _align = 'left') => ({ text: `${_text}`, color: THEME.text, padding: PAD_ROW, textAlign: _align });
const myDateCell  = _text => ({ text: `${_text}`, color: THEME.text, padding: PAD_ROW, textAlign: 'left' });

// Numeric cells (right-aligned)
const myBuyNumCell    = _text => ({ text: `${_text}`, color: THEME.buy,   padding: PAD_ROW, textAlign: 'right' });
const mySellNumCell   = _text => ({ text: `${_text}`, color: THEME.sell,  padding: PAD_ROW, textAlign: 'right' });
const myAwardNumCell  = _text => ({ text: `${_text}`, color: THEME.award, padding: PAD_ROW, textAlign: 'right' });
const myOtherNumCell  = _text => ({ text: `${_text}`, color: THEME.other, padding: PAD_ROW, textAlign: 'right' });

// Action column (bold)
const myActionBuyCell   = _text => ({ text: `${_text}`, color: THEME.buy,   padding: PAD_ROW, fontWeight: 'bold', textAlign: 'left' });
const myActionSellCell  = _text => ({ text: `${_text}`, color: THEME.sell,  padding: PAD_ROW, fontWeight: 'bold', textAlign: 'left' });
const myActionAwardCell = _text => ({ text: `${_text}`, color: THEME.award, padding: PAD_ROW, fontWeight: 'bold', textAlign: 'left' });
const myActionOtherCell = _text => ({ text: `${_text}`, color: THEME.other, padding: PAD_ROW, fontWeight: 'bold', textAlign: 'left' });

function myActionCellByType(_actionType, _textOverride = null) {
  const txt = _textOverride ?? _actionType;
  switch (_actionType) {
    case 'BUY':   return myActionBuyCell(txt);
    case 'SELL':  return myActionSellCell(txt);
    case 'AWARD': return myActionAwardCell(txt);
    default:      return myActionOtherCell(txt);
  }
}

const MY_SEPARATOR = { text: "", colspan: 6, borderBottom: `1px solid ${THEME.divider}` };

// ─────────────────────────────────────────────────────────────────────────────
// Overlay rows
// ─────────────────────────────────────────────────────────────────────────────
const overlayRows = [];

// Overall header
overlayRows.push({
  cells: [{
    colspan: 6,
    text: `${current.ticker}: Insider Transactions (Last ${myLookbackDays} Days)`,
    color: THEME.headerText,
    background: THEME.headerBg,
    padding: PAD_SEC,
    fontWeight: 'bold',
    textAlign: 'center',
    fontSize: myFontSize + 2
  }]
});
overlayRows.push({ cells: [ MY_SEPARATOR ] });

// ─────────────────────────────────────────────────────────────────────────────
// Terminal-style empty state: collapse all sections when no data
// ─────────────────────────────────────────────────────────────────────────────
if (!hasAnyTransactions) {
  overlayRows.push({
    cells: [{
      colspan: 6,
      text: 'NO INSIDER ACTIVITY DETECTED',
      color: THEME.mutedText,
      padding: '6px 6px',
      textAlign: 'center',
      fontWeight: 'bold'
    }]
  });

  paint_overlay('Insider Trades', { position: 'bottom_left', order: 'above_all' }, {
    fontSize: myFontSize,
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    background: THEME.panelBg,
    border: `2px solid ${THEME.border}`,
    rows: overlayRows
  });

  // Stop here so we don't render empty BUY/SELL/AWARD/OTHER blocks
  return;
}

// ─────────────────────────────────────────────────────────────────────────────
// Row builder per section
// ─────────────────────────────────────────────────────────────────────────────
function myMakeSectionRows(_actionType) {
  const rows = [];

  rows.push({
    cells: [
      myHeadCell('Date', 'left'),
      myHeadCell('Name', 'left'),
      myHeadCell('Position', 'left'),
      myHeadCell('Action', 'left'),
      myHeadCell('Shares', 'right'),
      myHeadCell('Value', 'right')
    ]
  });
  rows.push({ cells: [ MY_SEPARATOR ] });

  let count = 0;
  for (const t of myTransactions) {
    if (t.actionType !== _actionType) continue;

    const dateStr     = myFormatDateFromTimestamp(t.timestamp);
    const actionLabel = myDisplayActionText(t);

    const volStr = padNum(myFormatLargeNumber(t.volume), maxSharesLen);
    const valStr = padNum('$' + myFormatLargeNumber(t.netValue), maxValueLen);

    const volCell =
      _actionType === 'BUY'   ? myBuyNumCell(volStr)   :
      _actionType === 'SELL'  ? mySellNumCell(volStr)  :
      _actionType === 'AWARD' ? myAwardNumCell(volStr) :
                                myOtherNumCell(volStr);

    const valCell =
      _actionType === 'BUY'   ? myBuyNumCell(valStr)   :
      _actionType === 'SELL'  ? mySellNumCell(valStr)  :
      _actionType === 'AWARD' ? myAwardNumCell(valStr) :
                                myOtherNumCell(valStr);

    rows.push({
      cells: [
        myDateCell(dateStr),
        myValueCell(t.owner_name, 'left'),
        myValueCell(t.owner_title, 'left'),
        myActionCellByType(_actionType, actionLabel),
        volCell,
        valCell
      ]
    });

    count++;
  }

  if (!count) {
    rows.push({
      cells: [{
        text: `No ${_actionType} actions in the last ${myLookbackDays} days`,
        colspan: 6,
        color: THEME.mutedText,
        padding: PAD_ROW,
        textAlign: 'center'
      }]
    });
  }

  return rows;
}

const myBuyRows   = myMakeSectionRows('BUY');
const mySellRows  = myMakeSectionRows('SELL');
const myAwardRows = myMakeSectionRows('AWARD');
const myOtherRows = myMakeSectionRows('OTHER');

// ─────────────────────────────────────────────────────────────────────────────
// Section headers
// ─────────────────────────────────────────────────────────────────────────────
function mySectionHeader(_label, _bg, _fg) {
  return {
    cells: [{
      colspan: 6,
      text: `${_label}`,
      color: _fg,
      background: _bg,
      padding: PAD_SEC,
      fontWeight: 'bold',
      textAlign: 'center'
    }]
  };
}

const BUY_BG   = THEME.buyHeaderBg   || THEME.buy;
const SELL_BG  = THEME.sellHeaderBg  || THEME.sell;
const AWARD_BG = THEME.awardHeaderBg || THEME.award;
const OTHER_BG = THEME.otherHeaderBg || '#111111';

const SECTION_FG = THEME.sectionHeaderText || THEME.headerText || THEME.text;

// BUY
overlayRows.push(mySectionHeader('BUY', BUY_BG, SECTION_FG));
overlayRows.push({ cells: [ MY_SEPARATOR ] });
overlayRows.push(...myBuyRows);

// SELL
overlayRows.push(mySectionHeader('SELL', SELL_BG, SECTION_FG));
overlayRows.push({ cells: [ MY_SEPARATOR ] });
overlayRows.push(...mySellRows);

// AWARD (toggle)
if (showAwards) {
  overlayRows.push(mySectionHeader('AWARD', AWARD_BG, SECTION_FG));
  overlayRows.push({ cells: [ MY_SEPARATOR ] });
  overlayRows.push(...myAwardRows);
}

// OTHER (toggle)
if (showOther) {
  overlayRows.push(mySectionHeader('OTHER', OTHER_BG, SECTION_FG));
  overlayRows.push({ cells: [ MY_SEPARATOR ] });
  overlayRows.push(...myOtherRows);
}

// ─────────────────────────────────────────────────────────────────────────────
// Render overlay
// ─────────────────────────────────────────────────────────────────────────────
paint_overlay('Insider Trades', { position: 'bottom_left', order: 'above_all' }, {
  fontSize: myFontSize,
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
  background: THEME.panelBg,
  border: `2px solid ${THEME.border}`,
  rows: overlayRows
});
</code>