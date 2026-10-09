describe_indicator('Price Grid Fixed Interval', 'price');

// NOTE: Pine Script allowed up to 100 lines on each side of price, but
// TrendSpider requires a constant number of paint() calls on every run.
// To keep the chart usable we cap "Lines Each Side" at 20 (41 total grid
// lines). If you truly need more, duplicate the paint() blocks manually.
const MY_MAX_LINES_EACH_SIDE = 20;

const myLayoutTab = input.tab('Grid Settings');
const myGridRow = myLayoutTab.row();
const myGridSpacing = myGridRow.number('Grid Spacing', 25, { min: 0.01, max: 100000 });
const myMajorEvery = myGridRow.number('Major Line Every N Lines', 4, { min: 1, max: 100 });

const myRangeRow = myLayoutTab.row();
const myLinesEachSide = myRangeRow.number('Lines Above/Below Price', 10, { min: 1, max: MY_MAX_LINES_EACH_SIDE });
const myBarsBack = myRangeRow.number('Bars of History to Span Left', 200, { min: 10, max: 5000 });

const myDisplayRow = myLayoutTab.row();
const myShowLabels = myDisplayRow.boolean('Show Price Labels', true);
const myExtendRight = myDisplayRow.boolean('Extend Lines Right', true);

const myColorGroup = myLayoutTab.group('Colors');
const myColorRow = myColorGroup.row();
// These two color inputs are kept because color here is a conditional
// (major vs minor) choice applied across many separately-painted lines,
// not a single line's style, which the platform cannot auto-generate for.
const myMinorColor = myColorRow.color('Minor Line Color', 'rgba(0,128,0,0.35)');
const myMajorColor = myColorRow.color('Major Line Color', 'rgba(255,235,0,0.70)');

const myLastIndex = close.length - 1;
const myLastClose = close[myLastIndex];
const myCenterLevel = Math.floor(myLastClose / myGridSpacing) * myGridSpacing;

const myX1 = Math.max(0, myLastIndex - myBarsBack);

// FIX: line() requires toIndex to be a VALID candle index (it was
// throwing "to_index is invalid" because myX2 was set past the last
// available candle). We now anchor the second point to the last real
// candle and rely on "extendRight" to project the line further right
// if the user wants that, instead of manually picking an out-of-range index.
const myX2 = myLastIndex;

// Labels must also be anchored on the last real candle.
const myLabelIndex = myLastIndex;

// Signal accumulators (checked against the last candle's close, since the
// grid itself is anchored to the latest close, exactly like the Pine code
// which only recomputes "if barstate.islast").
let myTouchesMajorSignalValue = false;
let myTouchesMinorSignalValue = false;

// Small tolerance to call a close price "on" a grid line (float comparison).
const myTolerance = myGridSpacing * 0.001;

for (let myOffset = -MY_MAX_LINES_EACH_SIDE; myOffset <= MY_MAX_LINES_EACH_SIDE; myOffset += 1) {
	const myLineIndex = myOffset + MY_MAX_LINES_EACH_SIDE;
	const myIsActive = Math.abs(myOffset) <= myLinesEachSide;
	const myLevel = myCenterLevel + myOffset * myGridSpacing;
	const myStepsFromZero = Math.round(myLevel / myGridSpacing);
	const myIsMajor = (myStepsFromZero % myMajorEvery) === 0;
	const myColor = myIsMajor ? myMajorColor : myMinorColor;
	const myThickness = myIsMajor ? 2 : 1;

	const myLineSeries = myIsActive
		? line(myX1, myLevel, myX2, myLevel, myExtendRight)
		: series_of(null);

	const myPaintedLine = paint(myLineSeries, {
		name: `GridLine${myLineIndex}`,
		color: myColor,
		thickness: myThickness,
		style: 'line'
	});

	if (myIsActive && myShowLabels && myIsMajor) {
		paint_label_at_line(myPaintedLine, myLabelIndex, myLevel.toFixed(current.decimals), {
			color: myMajorColor,
			vertical_align: 'middle'
		});
	}

	if (myIsActive && Math.abs(myLastClose - myLevel) <= myTolerance) {
		if (myIsMajor) {
			myTouchesMajorSignalValue = true;
		}
		else {
			myTouchesMinorSignalValue = true;
		}
	}
}

// Scanning/strategy signals: true on the last candle when price sits on
// (within a small tolerance of) a major or minor grid level.
const myMajorTouchSignal = for_every(close, (_c, _p, _i) => _i === myLastIndex ? myTouchesMajorSignalValue : false);
const myMinorTouchSignal = for_every(close, (_c, _p, _i) => _i === myLastIndex ? myTouchesMinorSignalValue : false);

register_signal(myMajorTouchSignal, 'Price At Major Grid Line');
register_signal(myMinorTouchSignal, 'Price At Minor Grid Line');