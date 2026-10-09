describe_indicator('Custom Moving Averages', 'price');

// Simple moving averages, matching ta.sma(close, N) from the Pine script
const myMa20 = sma(close, 20);
const myMa72 = sma(close, 72);
const myMa200 = sma(close, 200);
const myMa420 = sma(close, 420);

paint(myMa20, { name: 'MA20', color: '#2962FF', thickness: 2 });
paint(myMa72, { name: 'MA72', color: '#2ECC71', thickness: 2 });
paint(myMa200, { name: 'MA200', color: '#EF5350', thickness: 2 });
paint(myMa420, { name: 'MA420', color: '#FF9800', thickness: 2 });

// Signals for scanners/alerts/strategies: crossovers between MA pairs
const myCrossUp20_72 = for_every(myMa20, myMa72, (_a, _b, _p, _i) => _i > 0 && myMa20[_i - 1] <= myMa72[_i - 1] && _a > _b);
const myCrossDown20_72 = for_every(myMa20, myMa72, (_a, _b, _p, _i) => _i > 0 && myMa20[_i - 1] >= myMa72[_i - 1] && _a < _b);

const myCrossUp72_200 = for_every(myMa72, myMa200, (_a, _b, _p, _i) => _i > 0 && myMa72[_i - 1] <= myMa200[_i - 1] && _a > _b);
const myCrossDown72_200 = for_every(myMa72, myMa200, (_a, _b, _p, _i) => _i > 0 && myMa72[_i - 1] >= myMa200[_i - 1] && _a < _b);

const myCrossUp200_420 = for_every(myMa200, myMa420, (_a, _b, _p, _i) => _i > 0 && myMa200[_i - 1] <= myMa420[_i - 1] && _a > _b);
const myCrossDown200_420 = for_every(myMa200, myMa420, (_a, _b, _p, _i) => _i > 0 && myMa200[_i - 1] >= myMa420[_i - 1] && _a < _b);

register_signal(myCrossUp20_72, 'MA20 Cross Above MA72');
register_signal(myCrossDown20_72, 'MA20 Cross Below MA72');
register_signal(myCrossUp72_200, 'MA72 Cross Above MA200');
register_signal(myCrossDown72_200, 'MA72 Cross Below MA200');
register_signal(myCrossUp200_420, 'MA200 Cross Above MA420');
register_signal(myCrossDown200_420, 'MA200 Cross Below MA420');