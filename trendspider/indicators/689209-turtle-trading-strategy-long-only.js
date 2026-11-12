<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Turtle Trading Strategy (Long-Only)', 'price', { mainColorInheritFrom: 'system_2_exit___20_day_low_' });
// ------------------------------- Inputs -------------------------------------------
const showSystem1   = input.boolean('Show System 1', true);
const showSystem2   = input.boolean('Show System 2', true);
const showAtrStop   = input.boolean('Show ATR Stop', true);
const showPyramids  = input.boolean('Show Pyramids', true);
const atrMult       = input.number('ATR Stop Multiplier', 2, { min: 0.1, max: 10 });
// Colours
const sys1EntryColor = input.color('System 1 Entry Color', '#00FFFF');
const sys2EntryColor = input.color('System 2 Entry Color', '#0066CC');
const sys1ExitColor  = input.color('System 1 Exit Color',  '#FF6B6B');
const sys2ExitColor  = input.color('System 2 Exit Color',  '#9370DB');
const atrStopColor   = input.color('ATR Stop Color',        '#FF00FF');
// ------------------------------- Fixed Turtle Params ------------------------------
const entryLen1   = 20;   // 20‑day high
const entryLen2   = 55;   // 55‑day high
const exitLen1    = 10;   // 10‑day low
const exitLen2    = 20;   // 20‑day low
const atrLen      = 20;   // ATR length
const pyramidStep = 0.5;  // in N units
const maxUnits    = 4;    // 1 + 3 adds
assert(close.length >= entryLen2, `Need at least ${entryLen2} bars for System 2 calculations`);
// ------------------------------- State --------------------------------------------
let state = {
  inTrade: false,
  system: 0,            // 1 or 2
  entry: 0,
  stop: 0,
  units: 0,
  nextAdd: 0,
  lastTradeWinner: false
};
// ------------------------------- Series Calculations ------------------------------
const chan20Hi = highest(high, entryLen1);
const chan55Hi = highest(high, entryLen2);
const chan10Lo = lowest(low,  exitLen1);
const chan20Lo = lowest(low,  exitLen2);
const atrN     = atr(atrLen);
const stopLine       = series_of(null);
const candleColors   = series_of(null);
const entryMarkers   = series_of(null);
const exitMarkers    = series_of(null);
// Scanner / strategy signals
const longBreakoutSignal  = series_of(false);
const pyramidAddSignal    = series_of(false);
const stopHitSignal       = series_of(false);
const channelExitSignal   = series_of(false);
const system1EntrySignal  = series_of(false);
const system2EntrySignal  = series_of(false);
const system1ExitSignal   = series_of(false);
const system2ExitSignal   = series_of(false);
const atrStopExitSignal   = series_of(false);
// ------------------------------- Main Loop ----------------------------------------
for (let i = Math.max(entryLen2, atrLen); i < close.length; i++) {
  const currentHigh  = high[i];
  const currentLow   = low[i];
  const currentClose = close[i];
  const currentAtr   = atrN[i];
  const prevChan20Hi = chan20Hi[i - 1];
  const prevChan55Hi = chan55Hi[i - 1];
  const prevChan10Lo = chan10Lo[i - 1];
  const prevChan20Lo = chan20Lo[i - 1];
  let exitTriggered     = false;
  let pyramidTriggered  = false;
  let entryTriggered    = false;
  let stopTriggered     = false;
  // ---------------- Exit Logic ------------------------------------
  if (state.inTrade) {
    // 1) ATR stop
    if (currentLow <= state.stop) {
      exitTriggered = true;
      stopTriggered = true;
      exitMarkers[i] = 'ATR';
      candleColors[i] = atrStopColor;
      stopHitSignal[i] = true;
      atrStopExitSignal[i] = true;
      state.lastTradeWinner = (currentClose > state.entry);
    }
    // 2) Channel exits
    else if (state.system === 1 && currentLow <= prevChan10Lo) {
      exitTriggered = true;
      exitMarkers[i] = 'S1X';
      candleColors[i] = sys1ExitColor;
      channelExitSignal[i] = true;
      system1ExitSignal[i] = true;
      state.lastTradeWinner = (currentClose > state.entry);
    }
    else if (state.system === 2 && currentLow <= prevChan20Lo) {
      exitTriggered = true;
      exitMarkers[i] = 'S2X';
      candleColors[i] = sys2ExitColor;
      channelExitSignal[i] = true;
      system2ExitSignal[i] = true;
      state.lastTradeWinner = (currentClose > state.entry);
    }
    // 3) Pyramid adds
    else if (showPyramids && state.units < maxUnits && currentHigh >= state.nextAdd) {
      pyramidTriggered = true;
      state.units += 1;
      // ---- Determine fill price for this add ----
      const fillPrice = (i + 1 < open.length) ? open[i + 1] : state.nextAdd;  // fallback if last bar
      // Re‑anchor stop 2 N below this fill
      state.stop = fillPrice - (atrMult * currentAtr);
      // Set up next add marker
      state.nextAdd = fillPrice + (pyramidStep * currentAtr);
      entryMarkers[i] = `+${state.units}`;
      candleColors[i] = (state.system === 1) ? sys1EntryColor : sys2EntryColor;
      pyramidAddSignal[i] = true;
    }
    // Maintain stop line if trade still live
    if (!exitTriggered) {
      stopLine[i] = state.stop;
    }
    // Reset state after exit
    if (exitTriggered) {
      state.inTrade = false;
      state.system  = 0;
      state.entry   = 0;
      state.stop    = 0;
      state.units   = 0;
      state.nextAdd = 0;
    }
  }
  // ---------------- Entry Logic -----------------------------------
  if (!state.inTrade && !exitTriggered) {
    // System 2 — 55‑day breakout (always allowed)
    if (currentHigh > prevChan55Hi) {
      const fillPrice = (i + 1 < open.length) ? open[i + 1] : currentHigh;
      entryTriggered  = true;
      state.inTrade   = true;
      state.system    = 2;
      state.entry     = fillPrice;
      state.stop      = fillPrice - (atrMult * currentAtr);
      state.units     = 1;
      state.nextAdd   = fillPrice + (pyramidStep * currentAtr);
      entryMarkers[i] = 'S2';
      candleColors[i] = sys2EntryColor;
      longBreakoutSignal[i] = true;
      system2EntrySignal[i] = true;
    }
    // System 1 — 20‑day breakout (skip after winner)
    else if (currentHigh > prevChan20Hi) {
      if (!state.lastTradeWinner) {
        const fillPrice = (i + 1 < open.length) ? open[i + 1] : currentHigh;
        entryTriggered  = true;
        state.inTrade   = true;
        state.system    = 1;
        state.entry     = fillPrice;
        state.stop      = fillPrice - (atrMult * currentAtr);
        state.units     = 1;
        state.nextAdd   = fillPrice + (pyramidStep * currentAtr);
        entryMarkers[i] = 'S1';
        candleColors[i] = sys1EntryColor;
        longBreakoutSignal[i] = true;
        system1EntrySignal[i] = true;
      } else {
        // Skip once after a winning trade
        state.lastTradeWinner = false;
      }
    }
    if (entryTriggered) {
      stopLine[i] = state.stop;
    }
  }
}
// ------------------------------- Plots --------------------------------------------
paint(showSystem1 ? chan20Hi : series_of(null), { name: 'System 1 Entry (20‑day high)', color: sys1EntryColor, style: 'ladder' });
paint(showSystem1 ? chan10Lo : series_of(null), { name: 'System 1 Exit  (10‑day low)',  color: sys1ExitColor,  style: 'ladder' });
paint(showSystem2 ? chan55Hi : series_of(null), { name: 'System 2 Entry (55‑day high)', color: sys2EntryColor, style: 'ladder' });
paint(showSystem2 ? chan20Lo : series_of(null), { name: 'System 2 Exit  (20‑day low)',  color: sys2ExitColor,  style: 'ladder' });
paint(showAtrStop ? stopLine : series_of(null), { name: 'ATR Stop Line', color: atrStopColor, style: 'ladder' });
color_candles(candleColors);
paint(entryMarkers, { style: 'labels_below', color: 'white', backgroundColor: 'transparent', name: 'Entry Markers' });
paint(exitMarkers,  { style: 'labels_above', color: 'white', backgroundColor: 'transparent', name: 'Exit Markers'  });
// ------------------------------- Signals ------------------------------------------
register_signal(pyramidAddSignal,   'Turtle Pyramid Add');
register_signal(system1EntrySignal, 'System 1 Entry');
register_signal(system2EntrySignal, 'System 2 Entry');
register_signal(system1ExitSignal,  'System 1 Exit');
register_signal(system2ExitSignal,  'System 2 Exit');
register_signal(atrStopExitSignal,  'ATR Stop Exit');</code>