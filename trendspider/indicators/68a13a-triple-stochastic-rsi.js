<code x-ref="code" class="hljs" data-clipboard-text>// ░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓████████▓▒░       ░▒▓███████▓▒░▒▓████████▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓███████▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
//    ░▒▓█▓▒░   ░▒▓███████▓▒░░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓██████▓▒░         ░▒▓██████▓▒░░▒▓██████▓▒░ ░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓██████▓▒░ ░▒▓███████▓▒░ ░▒▓██████▓▒░  
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░                    ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░                    ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓████████▓▒░      ░▒▓███████▓▒░░▒▓████████▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░                                                                                                                                                                      

describe_indicator('Triple Stochastic RSI', 'lower', { decimals: 2, warmup: '1000' });

// inputs
const kInput = input.number('K', 3, { min: 1, max: 50 });
const dInput = input.number('D', 3, { min: 1, max: 50 });
const rsiInput = input.number('RSI', 14, { min: 1, max: 50 });
const multiInput = input.number('2nd Multi', 3, { min: 2, max: 50 });
const multi2Input = input.number('3rd Multi', 6, { min: 2, max: 50 });
const overboughtInput = input.number('Overbought', 80, { min: 0, max: 100 });
const oversoldInput = input.number('Oversold', 20, { min: 0, max: 100 });
const showStatsInput = input('Show Stats Overlay?', 'Yes', ['Yes', 'No']) == 'Yes';

// funcs
const calculateAverageStreakLength = (_series) => {
    let streaks = [];
    let currentStreak = 0;
    for (let i = 0; i < _series.length; i++) {
        if (_series[i]) {
            currentStreak++;
        } else if (currentStreak > 0) {
            streaks.push(currentStreak);
            currentStreak = 0;
        }
    }
    if (currentStreak > 0) {
        streaks.push(currentStreak);
    }
    return streaks.length > 0 ? streaks.reduce((a, b) => a + b, 0) / streaks.length : 0;
};

const calculateCurrentStreakLength = (_series) => {
    let currentStreak = 0;
    for (let i = _series.length - 1; i >= 0; i--) {
        if (_series[i]) {
            currentStreak++;
        } else {
            break;
        }
    }
    return currentStreak;
};

const createOverlayStochStatRow = (currentAboveMid, currentBelowMid, avgAboveMid, avgBelowMid, stochTitle, stochTextColor) => {
	return { cells: [
		{ text: `${stochTitle}`, color: stochTextColor, paddingRight: '1.5em' },
		{ text: `${currentAboveMid > 0 ? currentAboveMid : currentBelowMid} ${currentAboveMid > 0 ? '▲' : '▼'}`, color: stochTextColor, paddingRight: '1.5em', textAlign: 'center' },
		{ text: `${avgAboveMid.toFixed(0)} ▲ / ${avgBelowMid.toFixed(0)} ▼`, color: stochTextColor, textAlign: 'center' }
	]};
};	

// logic
const fastK = stochastic_rsi(close, rsiInput, kInput);
const fastD = sma(fastK, dInput);
const slowK = stochastic_rsi(close, rsiInput * multiInput, kInput * multiInput);
const slowD = sma(slowK, dInput * multiInput);
const slowestK = stochastic_rsi(close, rsiInput * multi2Input, kInput * multi2Input);
const slowestD = sma(slowestK, dInput * multi2Input);

const fastTrendFlips = for_every(fastK, fastD, shift(fastK, -1), shift(fastD, -1), (k, d, pk, pd) => k > d && pk < pd ? '▼' : k < d && pk > pd ? '▲' : null);
const slowTrendFlips = for_every(slowK, slowD, shift(slowK, -1), shift(slowD, -1), (k, d, pk, pd) => k > d && pk < pd ? '▼' : k < d && pk > pd ? '▲' : null);

// k vs d states
const fastTrendLong = for_every(fastK, fastD, (k, d) => k > d);
const fastTrendShort = for_every(fastK, fastD, (k, d) => k < d);
const slowTrendLong = for_every(slowK, slowD, (k, d) => k > d);
const slowTrendShort = for_every(slowK, slowD, (k, d) => k < d);
const slowestTrendLong = for_every(slowestK, slowestD, (k, d) => k > d);
const slowestTrendShort = for_every(slowestK, slowestD, (k, d) => k < d);

// trend states
const fastTrendBullish = for_every(fastK, (k) => k >= 51);
const fastTrendBearish = for_every(fastK, (k) => k <= 49);
const slowTrendBullish = for_every(slowK, (k) => k >= 51);
const slowTrendBearish = for_every(slowK, (k) => k <= 49);
const slowestTrendBullish = for_every(slowestK, (k) => k >= 51);
const slowestTrendBearish = for_every(slowestK, (k) => k <= 49);

// mid avg stats
const fastAboveMid = calculateAverageStreakLength(fastK.map(_k => _k > 50));
const fastBelowMid = calculateAverageStreakLength(fastK.map(_k => _k < 50));
const slowAboveMid = calculateAverageStreakLength(slowK.map(_k => _k > 50));
const slowBelowMid = calculateAverageStreakLength(slowK.map(_k => _k < 50));
const slowestAboveMid = calculateAverageStreakLength(slowestK.map(_k => _k > 50));
const slowestBelowMid = calculateAverageStreakLength(slowestK.map(_k => _k < 50));

// mid current stats
const currentFastAboveMid = calculateCurrentStreakLength(fastK.map(_k => _k > 50));
const currentFastBelowMid = calculateCurrentStreakLength(fastK.map(_k => _k < 50));
const currentSlowAboveMid = calculateCurrentStreakLength(slowK.map(_k => _k > 50));
const currentSlowBelowMid = calculateCurrentStreakLength(slowK.map(_k => _k < 50));
const currentSlowestAboveMid = calculateCurrentStreakLength(slowestK.map(_k => _k > 50));
const currentSlowestBelowMid = calculateCurrentStreakLength(slowestK.map(_k => _k < 50));

// sentiment
const sentiment = for_every(slowK, slowestK, fastK, (_slow, _slowest, _fast) => {
    if (_slow > 50 && _slowest > 50) {
        return _fast < oversoldInput ? "Bullish Sentiment, Buy Zone" : "Bullish Sentiment";
    } else if (_slow < 50 && _slowest < 50) {
        return _fast > overboughtInput ? "Bearish Sentiment, Sell Zone" : "Bearish Sentiment";
    }
    return "Neutral Sentiment";
});

const currentSentiment = sentiment[sentiment.length - 1];

// current vs average streak states
const fastAboveAvgSignal = for_every(fastK, (_k, _i) => _k > 50 && currentFastAboveMid >= fastAboveMid);
const fastBelowAvgSignal = for_every(fastK, (_k, _i) => _k < 50 && currentFastBelowMid >= fastBelowMid);
const slowAboveAvgSignal = for_every(slowK, (_k, _i) => _k > 50 && currentSlowAboveMid >= slowAboveMid);
const slowBelowAvgSignal = for_every(slowK, (_k, _i) => _k < 50 && currentSlowBelowMid >= slowBelowMid);
const slowestAboveAvgSignal = for_every(slowestK, (_k, _i) => _k > 50 && currentSlowestAboveMid >= slowestAboveMid);
const slowestBelowAvgSignal = for_every(slowestK, (_k, _i) => _k < 50 && currentSlowestBelowMid >= slowestBelowMid);

// plots
const plotSlowestK = paint(slowestK, { name: 'Slowest K', color: '#E37222', thickness: 2 });
const plotSlowestD = paint(slowestD, { name: 'Slowest D', color: '#C95d10' });
const plotSlowK = paint(slowK, { name: 'Slow K', color: '#E040FB', thickness: 2 });
const plotSlowD = paint(slowD, { name: 'Slow D', color: '#9E04B9' });
const plotFastK = paint(fastK, { name: 'Fast K', color: '#00E676', thickness: 2 });
const plotFastD = paint(fastD, { name: 'Fast D', color: '#00A857' });

fill(plotSlowestK, plotSlowestD, '#C95d10', 0.2, 'Slowest Fill');
fill(plotSlowK, plotSlowD, '#9E04B9', 0.2, 'Slow Fill');
fill(plotFastK, plotFastD, '#00A857', 0.2, 'Fast Fill');

const plotOB = paint(horizontal_line(overboughtInput), { name: 'Overbought', color: '#666666' });
paint(horizontal_line(50), { name: 'Mid', color: '#444444' });
const plotOS = paint(horizontal_line(oversoldInput), { name: 'Oversold', color: '#666666' });
fill(plotOB, plotOS, '#444444', 0.2, 'Channel Fill');

paint_overlay('Stochastic Stats', { position: 'center_right' }, {
	padding: '2.5em',
	rows: showStatsInput ? [
		// headers
		{ cells: [{ text: `Stochastic Mid Stats (${fastK.length} Bars)`, color: 'var(--text-color)', colspan: 3, textAlign: 'center' }] },
		{ cells: [
			{ text: 'Stoch', color: 'var(--text-color)', paddingRight: '1.5em'},
			{ text: 'Current', color: 'var(--text-color)', paddingRight: '1.5em', textAlign: 'center' },
			{ text: 'Averages', color: 'var(--text-color)', textAlign: 'center' }
		]},
		// stoch stats
		createOverlayStochStatRow(currentFastAboveMid, currentFastBelowMid, fastAboveMid, fastBelowMid, 'Fast', '#00E676'),
		createOverlayStochStatRow(currentSlowAboveMid, currentSlowBelowMid, slowAboveMid, slowBelowMid, 'Slow', '#E040FB'),
		createOverlayStochStatRow(currentSlowestAboveMid, currentSlowestBelowMid, slowestAboveMid, slowestBelowMid, 'Slowest', '#E37222'),
		// sentiment footer
		{ cells: [{ text: `${currentSentiment}`, color: 'var(--text-color)', colspan: 3, textAlign: 'center' }] }
	] : []
});

// signals
// k vs d signals
register_signal(fastTrendLong.map(_value => _value === true), 'Fast Trend Long');
register_signal(fastTrendShort.map(_value => _value === true), 'Fast Trend Short');
register_signal(slowTrendLong.map(_value => _value === true), 'Slow Trend Long');
register_signal(slowTrendShort.map(_value => _value === true), 'Slow Trend Short');
register_signal(slowestTrendLong.map(_value => _value === true), 'Slowest Trend Long');
register_signal(slowestTrendShort.map(_value => _value === true), 'Slowest Trend Short');

// trend signals
register_signal(fastTrendBullish.map(_value => _value === true), 'Fast Stoch Long');
register_signal(fastTrendBearish.map(_value => _value === true), 'Fast Stoch Short');
register_signal(slowTrendBullish.map(_value => _value === true), 'Slow Stoch Long');
register_signal(slowTrendBearish.map(_value => _value === true), 'Slow Stoch Short');
register_signal(slowestTrendBullish.map(_value => _value === true), 'Slowest Stoch Long');
register_signal(slowestTrendBearish.map(_value => _value === true), 'Slowest Stoch Short');

register_signal(fastAboveAvgSignal, 'Fast Stoch At/Over Average Above Streak');
register_signal(fastBelowAvgSignal, 'Fast Stoch At/Over Average Below Streak');
register_signal(slowAboveAvgSignal, 'Slow Stoch At/Over Average Above Streak');
register_signal(slowBelowAvgSignal, 'Slow Stoch At/Over Average Below Streak');
register_signal(slowestAboveAvgSignal, 'Slowest Stoch At/Over Average Above Streak');
register_signal(slowestBelowAvgSignal, 'Slowest Stoch At/Over Average Below Streak');</code>