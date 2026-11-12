<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator(' Analyst Ratings Table ');

const myFontSize   = input.number('Font Size', 12, { min: 8, max: 30 });
const lookbackDays = input.number('Lookback Days', 5, { min: 1, max: 60 });
const useStriping  = input.boolean('Enable Striping', false);

const moment = library('moment-timezone');

// Use a consistent timezone for day boundaries + display
const TZ = 'America/New_York';

// === Fetch analyst ratings
const ratings = await request.analyst_ratings(String(constants.ticker));
assert(Array.isArray(ratings), `Failed to load ratings: ${ratings?.error || 'unknown error'}`);

// ─────────────────────────────────────────────────────────────────────────────
// ✅ IMPORTANT FIX: anchor lookback to REAL current time, not last candle time.
// Weekly/Monthly last candle can be days/weeks old, causing lookback to drift.
// ─────────────────────────────────────────────────────────────────────────────
const nowMs = Date.now();

// === Lookback start: last N calendar days (inclusive), anchored to ET midnight
const lookbackStart = moment.tz(nowMs, TZ).startOf('day').subtract(lookbackDays - 1, 'days');

// === Filter for last N calendar days (ET boundaries)
const recentRatings = ratings
  .map(r => ({ ...r, tsMs: (Number(r.timestamp) || 0) * 1000 }))
  .filter(r => r.tsMs > 0 && moment.tz(r.tsMs, TZ).isSameOrAfter(lookbackStart))
  .sort((a, b) => b.tsMs - a.tsMs);

// === Color helpers (refined palette)
const NEUTRAL = '#ffd966'; // goldenrod
const BG      = '#251f2b';
const STRIPE1 = '#595959';
const STRIPE2 = '#363636';

function getActionColor(actionRaw) {
  const a = String(actionRaw || '').toLowerCase();
  if (a.includes('upgrade'))   return 'limegreen';
  if (a.includes('downgrade')) return 'crimson';
  if (a.includes('confirm'))   return NEUTRAL;
  return 'dodgerblue';
}

function getTargetColorFromAction(actionRaw) {
  const base = getActionColor(actionRaw);
  switch (base) {
    case 'limegreen': return '#98fb98';  // palegreen
    case 'crimson':   return '#FC92A3';  // lightpink
    case NEUTRAL:     return '#ffd966';  // soft gold
    case 'dodgerblue':
    default:          return '#87cefa';  // lightskyblue
  }
}

function formatDate(tsMs) {
  // Display in ET consistently
  return moment.tz(tsMs, TZ).format('MM/DD HH:mm');
}

function getRankColor(rankRaw) {
  const rank = String(rankRaw || '').toLowerCase();
  if (rank === 'buy')  return 'limegreen';
  if (rank === 'hold') return NEUTRAL;
  if (rank === 'sell') return 'crimson';
  return 'white';
}

if (recentRatings.length === 0) {
  paint_overlay('Analyst Ratings', { position: 'bottom_right', order: 'above_all' }, {
    fontSize: myFontSize,
    background: BG,
    border: `1px solid #ffd966`,
    rows: [{
      cells: [{
        text: `🔴 No analyst ratings in the last ${lookbackDays} days for ${constants.ticker}`,
        color: 'white',
        background: STRIPE2,
        padding: '6px 10px'
      }]
    }]
  });
  return;
}

// === Table rows
const rows = [
  // Title
  {
    cells: [{
      colspan: 4,
      text: `🏷️ ${constants.ticker} Analyst Ratings (Last ${lookbackDays} Days)`,
      fontWeight: 'bold',
      color: 'orange',
      textAlign: 'center',
      padding: '8px 12px',
      fontSize: myFontSize + 1,
      background: BG
    }]
  },
  // Header row
  {
    cells: [
      { text: 'Time',  fontWeight: 'bold', padding: '4px 8px', color: 'lightgray', background: STRIPE2 },
      { text: 'Firm',  fontWeight: 'bold', padding: '4px 8px', color: 'lightgray', background: STRIPE2 },
      { text: 'Action / Target', fontWeight: 'bold', padding: '4px 8px', color: 'lightgray', background: STRIPE2 },
      { text: 'Rank',  fontWeight: 'bold', padding: '4px 8px', color: 'lightgray', background: STRIPE2 }
    ]
  }
];

// === Data rows
for (let i = 0; i < recentRatings.length; i++) {
  const r = recentRatings[i];
  const stripe = useStriping ? (i % 2 === 0 ? STRIPE1 : STRIPE2) : STRIPE2;

  const tsStr   = formatDate(r.tsMs);
  const firm    = r.analystCompany || 'Unknown';
  const action  = String(r.action || '').toUpperCase();
  const rankRaw = r.ratingCurrent || 'N/A';

  const actionColor = getActionColor(action);
  const targetColor = getTargetColorFromAction(action);

  const pt = r.pTarget ? `→ $${r.pTarget}` : '';
  const actionCellText = pt ? `${action} ${pt}` : action;

  rows.push({
    cells: [
      { text: tsStr, padding: '4px 8px', color: '#E0E0E0', background: stripe },
      { text: firm,  padding: '4px 8px', color: 'white',   background: stripe },
      {
        text: actionCellText,
        padding: '4px 8px',
        color: pt ? targetColor : actionColor,
        fontWeight: 'bold',
        background: stripe
      },
      {
        text: String(rankRaw).toUpperCase(),
        padding: '4px 8px',
        color: getRankColor(rankRaw),
        fontWeight: 'bold',
        background: stripe
      }
    ]
  });
}

// === Render overlay
paint_overlay('Analyst Ratings', { position: 'bottom_right', order: 'above_all' }, {
  fontSize: myFontSize,
  background: BG,
  border: `1px solid #ffd966`,
  rows
});
</code>