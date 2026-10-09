describe_indicator('Simple Price Display', 'price');

// This indicator reproduces a TradingView Pine Script that only
// displays current price and % change as a text label (via a
// table) on the last bar. TrendSpider has no table primitive, so
// we use paint_overlay() to render an equivalent text box, and we
// expose the bullish/bearish condition through register_signal()
// so it can be used in scanners/alerts/strategies.

// Percentage change vs previous close
const myChgPct = for_every(close, (_c, _prev, _i) => {
	return _i > 0 ? ((_c - close[_i - 1]) / close[_i - 1]) * 100 : 0;
});

const myIsBull = for_every(myChgPct, _chg => _chg >= 0);

// Register signals so this logic is usable in scanners/alerts/strategies
register_signal(myIsBull, "Bullish Change");
register_signal(for_every(myIsBull, _b => !_b), "Bearish Change");

// Build the display text only for the last bar
const myLastIndex = close.length - 1;
const myLastClose = close[myLastIndex];
const myLastChgPct = myChgPct[myLastIndex];
const myIsBullLast = myIsBull[myLastIndex];

const mySign = myIsBullLast ? "+" : "";
const myPriceColor = myIsBullLast ? "#35ff00" : "#ff0000";
const myPriceStr = myLastClose.toFixed(current.decimals);
const myChgStr = mySign + myLastChgPct.toFixed(2) + "%";
const myDisplayText = myPriceStr + "  (" + myChgStr + ")";

// Render the text box in the top right corner, mimicking the
// invisible/borderless table from the Pine script
paint_overlay("PriceDisplay", { position: "top_right", offset_x: 10, offset_y: 10 }, {
	rows: [{
		cells: [{
			text: myDisplayText,
			color: myPriceColor,
			font_size: "22px",
			align: "right"
		}]
	}]
});