describe_indicator('COT Net Positioning', 'lower');

// Pine Script library "LibraryCOT" is a TradingView-specific library.
// There is no equivalent in the TrendSpider Custom JS API: there is
// no COT (Commitment of Traders) data source available (request.*
// functions do not expose COT data). This means this indicator can
// not be reproduced, not even approximately.

const myShowCommercials = input.boolean('Commercials net', true);
const myShowNonCommercials = input.boolean('NonCommercials net', true);
const myShowRetail = input.boolean('Retail net', false);

// Since COT data cannot be fetched, we paint constant null series,
// keeping the same number/order of paint() calls and the same names
// as the original script would have produced.
paint(myShowCommercials ? series_of(null) : series_of(null), { name: 'Commercials net', color: 'blue', thickness: 3 });
paint(myShowNonCommercials ? series_of(null) : series_of(null), { name: 'Non Commercials net', color: 'red', thickness: 3 });
paint(myShowRetail ? series_of(null) : series_of(null), { name: 'Retail net', color: 'green', thickness: 2 });
paint(horizontal_line(0), { name: 'Zero', color: 'black', style: 'dotted', thickness: 1 });

register_signal(series_of(false), 'Commercials Net Positive');
register_signal(series_of(false), 'Non Commercials Net Positive');
register_signal(series_of(false), 'Retail Net Positive');