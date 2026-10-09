describe_indicator('Moving Averages 350 700 1400', 'price');

// MA type selector (SMA or EMA), matching Pine Script's maType input
const myMAType = input.select('MA Type', 'SMA', ['SMA', 'EMA']);

// Toggles for each MA, matching Pine Script's show1/show2/show3
const myShow1 = input.boolean('MA 1 (350)', true);
const myShow2 = input.boolean('MA 2 (700)', true);
const myShow3 = input.boolean('MA 3 (1400)', true);

// Hardcoded lengths, exactly as in the Pine Script
const myLen1 = 350;
const myLen2 = 700;
const myLen3 = 1400;

// Pick the MA function based on user selection
const myComputeMA = myMAType === 'EMA' ? ema : sma;

const myMA1 = myComputeMA(close, myLen1);
const myMA2 = myComputeMA(close, myLen2);
const myMA3 = myComputeMA(close, myLen3);

// Paint lines, respecting toggles (null series when hidden, to keep
// paint() call count/params constant across all parameter combos)
paint(myShow1 ? myMA1 : constants.empty_series, { name: 'MA350', color: '#2196F3', thickness: 2 });
paint(myShow2 ? myMA2 : constants.empty_series, { name: 'MA700', color: '#E91E63', thickness: 2 });
paint(myShow3 ? myMA3 : constants.empty_series, { name: 'MA1400', color: '#9C27B0', thickness: 2 });

// Signals for scanning/strategy: crossovers between the 3 MAs
const myCrossUp1v2 = for_every(myMA1, myMA2, (_a, _b, _prev, _i) => _i > 0 && myMA1[_i - 1] <= myMA2[_i - 1] && _a > _b);
const myCrossDown1v2 = for_every(myMA1, myMA2, (_a, _b, _prev, _i) => _i > 0 && myMA1[_i - 1] >= myMA2[_i - 1] && _a < _b);

const myCrossUp2v3 = for_every(myMA2, myMA3, (_a, _b, _prev, _i) => _i > 0 && myMA2[_i - 1] <= myMA3[_i - 1] && _a > _b);
const myCrossDown2v3 = for_every(myMA2, myMA3, (_a, _b, _prev, _i) => _i > 0 && myMA2[_i - 1] >= myMA3[_i - 1] && _a < _b);

const myCrossUp1v3 = for_every(myMA1, myMA3, (_a, _b, _prev, _i) => _i > 0 && myMA1[_i - 1] <= myMA3[_i - 1] && _a > _b);
const myCrossDown1v3 = for_every(myMA1, myMA3, (_a, _b, _prev, _i) => _i > 0 && myMA1[_i - 1] >= myMA3[_i - 1] && _a < _b);

register_signal(myCrossUp1v2, 'MA350 Crosses Above MA700');
register_signal(myCrossDown1v2, 'MA350 Crosses Below MA700');
register_signal(myCrossUp2v3, 'MA700 Crosses Above MA1400');
register_signal(myCrossDown2v3, 'MA700 Crosses Below MA1400');
register_signal(myCrossUp1v3, 'MA350 Crosses Above MA1400');
register_signal(myCrossDown1v3, 'MA350 Crosses Below MA1400');