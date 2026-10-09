// Draws price zones (boxes) and horizontal levels from two short text inputs.
// Also exposes a fixed set of scanning signals (price vs levels/zones), since
// scanning/strategy requires register_signal() outputs that Pine does not have.
describe_indicator('Manual Zone and Level Plotter', 'price');

const myZonesTab = input.tab('Zones and Levels');
const myBoxStr = myZonesTab.text('Zones', '', { hide_in_legend: true });
const myLvStr = myZonesTab.text('Levels', '', { hide_in_legend: true });

const myStyleTab = input.tab('Style');
const myShowPx = myStyleTab.boolean('Show price tags', true);
const myFillOpacityPct = myStyleTab.number('Zone opacity percent', 8, { min: 1, max: 50 });
const myLineW = myStyleTab.number('Line width', 1, { min: 1, max: 3 });

// Maximum number of items supported per category. Reduced from 10 to 5
// because each category paints 2 lines per slot, across 5 categories;
// combined with the 4 register_signal() outputs, the previous value of
// 10 exceeded the platform's limit of 70 total output series
// (5 categories * 10 slots * 2 lines = 100, well above the limit).
// With 5 slots: 5 categories * 5 slots * 2 lines = 50, plus 4 signals = 54,
// safely under the 70 output series cap.
const MY_MAX_ITEMS = 5;

// Replicates f_seg(): extracts the body of a group tagged with "tag"
// (e.g. "G" -> "4371.83-4400") from a ";"-separated string.
function myExtractSegment(_src, _tag) {
	let myFound = '';
	if (_src.length > 0) {
		const myClean = _src.replace(/ /g, '').replace(/\n/g, '');
		const myParts = myClean.split(';');
		for (const myPart of myParts) {
			if (myPart.length > 1 && myPart.startsWith(_tag)) {
				myFound = myPart.substring(1);
			}
		}
	}
	return myFound;
}

// Replicates f_draw(): parses a body like "4371.83-4400,4350" into a
// list of { top, bot } items (ranges become boxes, single numbers
// become zero-height "lines").
function myParseGroup(_body) {
	const myResult = [];
	if (_body.length > 0) {
		const myItems = _body.split(',');
		for (const myItem of myItems) {
			const myPair = myItem.split('-');
			if (myPair.length === 2) {
				const myA = parseFloat(myPair[0]);
				const myB = parseFloat(myPair[1]);
				if (!isNaN(myA) && !isNaN(myB)) {
					myResult.push({ top: Math.max(myA, myB), bot: Math.min(myA, myB) });
				}
			}
			else {
				const myP = parseFloat(myItem);
				if (!isNaN(myP)) {
					myResult.push({ top: myP, bot: myP });
				}
			}
		}
	}
	return myResult.slice(0, MY_MAX_ITEMS);
}

const myGItems = myParseGroup(myExtractSegment(myBoxStr, 'G'));
const myOItems = myParseGroup(myExtractSegment(myBoxStr, 'O'));
const myXItems = myParseGroup(myExtractSegment(myBoxStr, 'X'));
const myRItems = myParseGroup(myExtractSegment(myLvStr, 'R'));
const mySItems = myParseGroup(myExtractSegment(myLvStr, 'S'));

const myCategories = [
	{ items: myGItems, color: 'rgb(38,166,154)', nameTop: 'G Top', nameBot: 'G Bot' },
	{ items: myOItems, color: 'rgb(255,152,0)', nameTop: 'O Top', nameBot: 'O Bot' },
	{ items: myXItems, color: 'rgb(144,164,174)', nameTop: 'X Top', nameBot: 'X Bot' },
	{ items: myRItems, color: 'rgb(239,83,80)', nameTop: 'R Top', nameBot: 'R Bot' },
	{ items: mySItems, color: 'rgb(38,166,154)', nameTop: 'S Top', nameBot: 'S Bot' }
];

const myDecimals = current.decimals || 2;

for (const myCategory of myCategories) {
	for (let mySlot = 0; mySlot < MY_MAX_ITEMS; mySlot += 1) {
		const myItem = myCategory.items[mySlot];
		const myTopSeries = myItem ? horizontal_line(myItem.top) : constants.empty_series;
		const myBotSeries = myItem ? horizontal_line(myItem.bot) : constants.empty_series;

		const myTopPainted = paint(myTopSeries, {
			name: myCategory.nameTop + ' ' + (mySlot + 1),
			color: myCategory.color,
			thickness: myLineW,
			style: 'line'
		});
		const myBotPainted = paint(myBotSeries, {
			name: myCategory.nameBot + ' ' + (mySlot + 1),
			color: myCategory.color,
			thickness: myLineW,
			style: 'line'
		});

		fill(myTopPainted, myBotPainted, myCategory.color, (100 - myFillOpacityPct) / 100);

		if (myShowPx && myItem) {
			paint_label_at_line(myTopPainted, close.length - 1, myItem.top.toFixed(myDecimals));
			if (myItem.bot !== myItem.top) {
				paint_label_at_line(myBotPainted, close.length - 1, myItem.bot.toFixed(myDecimals));
			}
		}
	}
}

// Scanning / strategy signals. Pine code has no signals of its own, so
// these are derived outputs useful for scanners/alerts/backtests:
// - price breaking above the highest R level
// - price breaking below the lowest S level
// - price trading inside the first G zone / first O zone
const myHighestR = myRItems.length ? Math.max(...myRItems.map(_i => _i.top)) : null;
const myLowestS = mySItems.length ? Math.min(...mySItems.map(_i => _i.bot)) : null;
const myFirstG = myGItems.length ? myGItems[0] : null;
const myFirstO = myOItems.length ? myOItems[0] : null;

const myResistanceBreakSignal = for_every(close, _c => myHighestR !== null && _c > myHighestR);
const mySupportBreakSignal = for_every(close, _c => myLowestS !== null && _c < myLowestS);
const myInsidePrimaryZoneSignal = for_every(close, _c => myFirstG !== null && _c <= myFirstG.top && _c >= myFirstG.bot);
const myInsideSecondaryZoneSignal = for_every(close, _c => myFirstO !== null && _c <= myFirstO.top && _c >= myFirstO.bot);

register_signal(myResistanceBreakSignal, 'Resistance Break');
register_signal(mySupportBreakSignal, 'Support Break');
register_signal(myInsidePrimaryZoneSignal, 'Inside Primary Zone');
register_signal(myInsideSecondaryZoneSignal, 'Inside Secondary Zone');