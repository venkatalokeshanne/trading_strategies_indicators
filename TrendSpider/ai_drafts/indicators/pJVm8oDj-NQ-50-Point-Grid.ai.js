// NOTE: This is a best-effort translation of the Pine Script grid tool.
// TrendSpider doesn't support dynamically creating/destroying line objects
// like Pine's line.new()/array, so this script paints a FIXED number of
// horizontal levels (horizontal_line()) centered on the last close, which
// is functionally equivalent to the Pine script's "extend both" grid.
// To respect the platform rule that the number of paint() calls must be
// constant, the max amount of levels on each side is capped at 20 (41
// total lines), instead of Pine's max of 200 (401 lines). This keeps the
// chart readable and performant; raise MAX_LEVELS_EACH_SIDE if you really
// need more, but be aware this will add more paint() calls permanently.
describe_indicator('NQ 50 Point Grid', 'price');

const GRID_SIZE = 50;
const MAX_LEVELS_EACH_SIDE = 20;
const MAX_TOTAL_LEVELS = MAX_LEVELS_EACH_SIDE * 2 + 1;

const myLevelsEachSide = input.number('Levels above and below price', 20, { min: 1, max: MAX_LEVELS_EACH_SIDE });
const myShowPriceLabels = input.boolean('Show price labels', true);
const myEmphasizeHundreds = input.boolean('Emphasize 100 point levels', true);

// Default colors/widths; the platform already provides per-line color
// controls, these are just the initial defaults.
const myLevelColor = 'rgba(128,128,128,0.45)';
const myHundredColor = 'rgba(0,80,220,0.8)';
const myLevelWidth = 1;
const myHundredWidth = 2;

// Pine checks syminfo.root; we approximate with current.root / current.ticker.
const myIsNq = (current.root === 'NQ' || current.root === 'MNQ' ||
	current.ticker === 'NQ' || current.ticker === 'MNQ');

const myLastClose = close[close.length - 1];
const myCenterLevel = Math.floor(myLastClose / GRID_SIZE) * GRID_SIZE;
const myLastIndex = close.length - 1;

for (let myIndex = 0; myIndex < MAX_TOTAL_LEVELS; myIndex += 1) {
	const myGridOffset = myIndex - MAX_LEVELS_EACH_SIDE;
	const myIsActive = myIsNq && Math.abs(myGridOffset) <= myLevelsEachSide;

	const myGridPrice = myCenterLevel + myGridOffset * GRID_SIZE;
	const myIsHundred = Math.round(myGridPrice / GRID_SIZE) % 2 === 0;
	const myCurrentColor = (myEmphasizeHundreds && myIsHundred) ? myHundredColor : myLevelColor;
	const myCurrentWidth = (myEmphasizeHundreds && myIsHundred) ? myHundredWidth : myLevelWidth;

	const myLineSeries = myIsActive ? horizontal_line(myGridPrice) : series_of(null);

	const myPaintedLine = paint(myLineSeries, {
		name: `Level${myIndex}`,
		color: myCurrentColor,
		thickness: myCurrentWidth,
		style: 'line'
	});

	if (myShowPriceLabels && myIsActive) {
		paint_label_at_line(myPaintedLine, myLastIndex, `${myGridPrice}`, {
			color: myCurrentColor,
			vertical_align: 'middle'
		});
	}
}

// Warning overlay replicating Pine's table.cell warning for non NQ charts.
paint_overlay('GridWarning', { position: 'top_right' }, {
	rows: myIsNq ? [] : [{
		cells: [{
			text: 'NQ 50-Point Grid: use this indicator on an NQ chart.',
			color: 'white',
			background_color: 'rgba(220,0,0,0.8)'
		}]
	}]
});

// Scanning / alert signal: true when price is within 1 point of any
// active 50-point grid level (useful for alerts "price touched a level").
const mySignal = for_every(close, _close => {
	const myDistanceFromGrid = Math.abs(_close - Math.round(_close / GRID_SIZE) * GRID_SIZE);
	return myDistanceFromGrid <= 1;
});
register_signal(mySignal, 'Price At Grid Level');