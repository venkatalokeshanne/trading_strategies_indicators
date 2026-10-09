describe_indicator('My Rules Watermark');
// This indicator is a pure text watermark (title + trading rules),
// just like the original Pine Script. It has no numeric output,
// so it cannot generate scanner, alert or strategy signals -
// there is nothing to "map out" in terms of trading logic.
const titleTab = input.tab('Title');
const myTitle = titleTab.text('Title', 'MY TRADING RULES');
const myTitleSize = titleTab.select('Title Size', 'huge', ['tiny', 'small', 'normal', 'large', 'huge']);
const myTitleColor = input.color('Title Color', 'rgba(128,128,128,0.4)');

const rulesTab = input.tab('Rules');
const myRule1 = rulesTab.text('Rule 1', '1. Trade only A+ setups');
const myRule2 = rulesTab.text('Rule 2', '2. Risk max 1% per trade');
const myRule3 = rulesTab.text('Rule 3', '3. Wait for confirmation');
const myRule4 = rulesTab.text('Rule 4', '4. No revenge trading');
const myRule5 = rulesTab.text('Rule 5', '5. Respect the stop loss');
const myRule6 = rulesTab.text('Rule 6', '6. 2 losses, stop for the day');
const myRule7 = rulesTab.text('Rule 7', '');
const myRule8 = rulesTab.text('Rule 8', '');

const styleTab = input.tab('Style');
const myRulesSize = styleTab.select('Rules Size', 'normal', ['tiny', 'small', 'normal', 'large', 'huge']);
const myRulesColor = input.color('Rules Color', 'rgba(128,128,128,0.6)');
// NOTE: paint_overlay() only accepts the 4 corner positions
// (top_left, top_right, bottom_left, bottom_right). The
// "middle_*" and "*_center" values are not valid and were
// causing the "invalid position value" error. Restricted the
// selectable options to the supported corner positions.
const myPosition = styleTab.select('Position', 'top_right', [
	'top_left', 'top_right',
	'bottom_left', 'bottom_right'
]);
const myAlign = styleTab.select('Text Align', 'center', ['left', 'center', 'right']);
const myShowSymbol = styleTab.boolean('Show Symbol / Timeframe', false);

// map "size" names to approximate font pixel sizes
const mySizeMap = {
	tiny: '10px',
	small: '12px',
	normal: '14px',
	large: '18px',
	huge: '24px'
};

const myRulesList = [myRule1, myRule2, myRule3, myRule4, myRule5, myRule6, myRule7, myRule8].filter(_r => _r !== '');
const mySymbolLine = myShowSymbol ? `${current.ticker}  -  ${current.resolution}` : '';
const myBodyLines = (mySymbolLine ? [mySymbolLine] : []).concat(myRulesList);
const myBodyText = myBodyLines.join('\n');

paint_overlay('MyRulesWatermark', { position: myPosition }, {
	rows: [{
		cells: [{
			text: myTitle,
			color: myTitleColor,
			font_size: mySizeMap[myTitleSize],
			align: myAlign
		}]
	}, {
		cells: [{
			text: myBodyText,
			color: myRulesColor,
			font_size: mySizeMap[myRulesSize],
			align: myAlign
		}]
	}]
});