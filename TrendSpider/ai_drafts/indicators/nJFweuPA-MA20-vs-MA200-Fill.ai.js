describe_indicator('MA20 vs MA200 Fill', 'price');

// Compute the two moving averages exactly as in the Pine script
const myMa20 = sma(close, 20);
const myMa200 = sma(close, 200);

// Paint the two MA lines
const myLine1 = paint(myMa20, { name: 'MA20', color: 'blue', thickness: 2 });
const myLine2 = paint(myMa200, { name: 'MA200', color: 'orange', thickness: 2 });

// Dynamic cloud color: green when MA20 above MA200, red otherwise
color_cloud(myMa20, myMa200, 'green', 'red', 'Above', 'Below', 0.2);

// Signals for scanning/alerts/strategy use
const myBullishSignal = for_every(myMa20, myMa200, (_fast, _slow) => _fast > _slow);
const myBearishSignal = for_every(myMa20, myMa200, (_fast, _slow) => _fast < _slow);

// Crossover signals (bar where MA20 crosses MA200)
const myCrossUp = for_every(myMa20, myMa200, (_fast, _slow, _prev, _idx) => {
	if (_idx === 0) return false;
	return _fast > _slow && myMa20[_idx - 1] <= myMa200[_idx - 1];
});
const myCrossDown = for_every(myMa20, myMa200, (_fast, _slow, _prev, _idx) => {
	if (_idx === 0) return false;
	return _fast < _slow && myMa20[_idx - 1] >= myMa200[_idx - 1];
});

register_signal(myBullishSignal, 'MA20 Above MA200');
register_signal(myBearishSignal, 'MA20 Below MA200');
register_signal(myCrossUp, 'MA20 Crosses Above MA200');
register_signal(myCrossDown, 'MA20 Crosses Below MA200');