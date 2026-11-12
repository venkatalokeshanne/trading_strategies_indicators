<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Pre-market High/Low', 'overlay');

// Require intraday (< 120m)
assert(
  Number(current.resolution) < 120 || current.resolution.endsWith('S') || current.resolution.endsWith('T'),
  "This indicator only supports chart resolutions less than 120 minutes.");

const moment = library('moment-timezone');

// ---- Inputs ----
const nyseStartHour   = input.number('Start Hour',   4,  { min: 0, max: 23 });
const nyseStartMinute = input.number('Start Minute', 0,  { min: 0, max: 59 });
const nyseEndHour     = input.number('End Hour',     9,  { min: 0, max: 23 });
const nyseEndMinute   = input.number('End Minute',   29, { min: 0, max: 59 });
const useFuturesTime  = input.boolean('Use Time Diff Cal', false, { hide_in_legend: true });
const localTimeDiff   = input.number('local-Mountain Time Diff', 1, { min: 0, max: 11, hide_in_legend: true });

// ---- Fetch extended hours data to get pre-market range ----
const extHoursData = await request.history(current.ticker, current.resolution, { ext_session: true });
assert(!extHoursData.error, `Error fetching extended hours data: ${extHoursData.error}`);

// ---- Helpers ----
function adjustHour(h) {
  return useFuturesTime ? (h - localTimeDiff + 24) % 24 : (h % 24);
}

function inWindow(dt, sH, sM, eH, eM) {
  // Handles both same-day and midnight-cross windows
  if (sH < eH || (sH === eH && sM <= eM)) {
    return (
      (dt.hours > sH || (dt.hours === sH && dt.minutes >= sM)) &&
      (dt.hours < eH || (dt.hours === eH && dt.minutes <= eM))
    );
  } else {
    // crosses midnight
    return (
      (dt.hours > sH || (dt.hours === sH && dt.minutes >= sM)) ||
      (dt.hours < eH || (dt.hours === eH && dt.minutes <= eM))
    );
  }
}

// ---- Compute pre-market ranges from extended hours data ----
const preMarketRangeByDay = {};

for (let extIndex = 0; extIndex < extHoursData.time.length; extIndex++) {
  const ts = extHoursData.time[extIndex];
  const dt = time_of(ts);
  const dayStart = moment(ts * 1000).startOf('day').unix();
  
  const sH = adjustHour(nyseStartHour);
  const eH = adjustHour(nyseEndHour);
  const insidePM = inWindow(dt, sH, nyseStartMinute, eH, nyseEndMinute);
  
  if (insidePM) {
    if (!preMarketRangeByDay[dayStart]) {
      preMarketRangeByDay[dayStart] = {
        high: extHoursData.high[extIndex],
        low: extHoursData.low[extIndex]
      };
    } else {
      preMarketRangeByDay[dayStart].high = Math.max(preMarketRangeByDay[dayStart].high, extHoursData.high[extIndex]);
      preMarketRangeByDay[dayStart].low = Math.min(preMarketRangeByDay[dayStart].low, extHoursData.low[extIndex]);
    }
  }
}

// ---- Series ----
const pmHigh = series_of(null);
const pmLow  = series_of(null);

// ---- State ----
let currentDayStart = 0;

// ---- Main loop - assign pre-market ranges to current chart candles ----
for (let i = 0; i < time.length; i++) {
  const ts = time[i];
  const dayStart = moment(ts * 1000).startOf('day').unix();
  
  // New day?
  if (dayStart !== currentDayStart) {
    currentDayStart = dayStart;
    
    // carry forward previous day's values initially
    if (i > 0) {
      pmHigh[i] = pmHigh[i - 1];
      pmLow[i]  = pmLow[i - 1];
    }
  } else {
    // same day — carry forward
    if (i > 0) {
      pmHigh[i] = pmHigh[i - 1];
      pmLow[i]  = pmLow[i - 1];
    }
  }
  
  // Assign the pre-market range for this day
  const pmRange = preMarketRangeByDay[currentDayStart];
  if (pmRange) {
    pmHigh[i] = pmRange.high;
    pmLow[i]  = pmRange.low;
  }
  
  // Set NULL on the LAST candle of the day for line breaks
  if (i < time.length - 1) {
    const nextDayStart = moment(time[i + 1] * 1000).startOf('day').unix();
    if (nextDayStart !== currentDayStart) {
      pmHigh[i] = null;
      pmLow[i]  = null;
    }
  }
}

// ---- Paint ----
const pmhPainted = paint(pmHigh, { color: 'gray', name: 'PMH', style: 'line' });
const pmlPainted = paint(pmLow,  { color: 'gray', name: 'PML',  style: 'line' });
</code>