/*
 * ── Converted from TradingView Pine Script ─────────────────────────────
 * Original     : Setup Checklist
 * Author       : Dipologist
 * Source URL   : https://www.tradingview.com/script/a886kJ0b-Setup-Checklist
 * Pine version : v6
 * Licence      : not stated
 * Type         : indicator
 * Placement    : overlay
 * Status       : PARTIAL
 * Converted    : 2026-10-09 by Claude (pine-to-trendspider skill), from a TrendSpider-AI draft
 * TrendSpider name : Setup Checklist_TV
 *
 * Deviations from the original: Reviewed AI draft; checklist table via paint_overlay (static image: tick boxes and
 *   re-apply to refresh); input titles shortened.
 * Not carried over: none.
 * ────────────────────────────────────────────────────────────────────────
 */
describe_indicator('Setup Checklist_TV', 'price');
const myListTab = input.tab('Checklist');
const myStep1 = myListTab.boolean('1. Draw identified', false);
const myStep2 = myListTab.boolean('2. Manipulation sweep', false);
const myStep3 = myListTab.boolean('3. Sweep inside 15m+ FVG', false);
const myStep4 = myListTab.boolean('4. Reaction off the gap', false);
const myStep5 = myListTab.boolean('5. V-shaped recovery', false);
const myStep6 = myListTab.boolean('6. iFVG formed', false);
const myStep7 = myListTab.boolean('7. Entry plan set', false);
const myDisplayTab = input.tab('Display');
const myPosition = myDisplayTab.select('Table Position', 'bottom_right', ['top_right', 'middle_right', 'bottom_right', 'top_left', 'bottom_left']);
const mySteps = [myStep1, myStep2, myStep3, myStep4, myStep5, myStep6, myStep7];
const myCount = mySteps.filter(_s => _s).length;
const myAllDone = myCount === 7;
const myNextTexts = ['STEP 1: NAME THE DRAW', 'WAIT: SWEEP', 'CHECK: 15m FVG?', 'WAIT: REACTION', 'WAIT: V-SHAPE', 'WAIT: iFVG', 'SET ENTRY PLAN'];
const myFirstOpen = mySteps.findIndex(_s => !_s);
const myNextText = myFirstOpen === -1 ? 'ALL CLEAR - TAKE IT' : myNextTexts[myFirstOpen];
const myLabels = ['1 Draw identified', '2 Manipulation sweep', '3 Inside 15m+ FVG', '4 Reaction off gap', '5 V-shape recovery', '6 iFVG formed', '7 Entry plan set'];
const myRow = (_label, _done) => ({ cells: [
	{ text: _label, color: _done ? '#000000' : '#808080', background_color: '#f5f5f5' },
	{ text: _done ? 'OK' : 'X', color: _done ? '#008000' : '#d00000', background_color: '#f5f5f5' }
] });
const myFooterBg = myAllDone ? '#008000' : '#ffb74d';
paint_overlay('Setup Checklist Table', { position: myPosition }, {
	rows: [
		{ cells: [{ text: 'SWEEP TO DRAW', color: '#000000', background_color: '#f5f5f5' }, { text: myCount + '/7', color: myAllDone ? '#008000' : '#000000', background_color: '#f5f5f5' }] },
		...myLabels.map((_l, _i) => myRow(_l, mySteps[_i])),
		{ cells: [{ text: myNextText, color: myAllDone ? '#ffffff' : '#000000', background_color: myFooterBg }, { text: '', background_color: myFooterBg }] }
	]
});
register_signal(series_of(myAllDone), 'All Seven Steps Checked');
