<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('SPY SPX ES Price Converter [Pt]', 'price', { shortName: 'SPY/SPX/ES Conv [Pt]' });

const enableSpy = input.boolean('SPY on', true);
const spyMult = input.number('SPY increment', 1, { min: 0.1, step: 0.5 });
const spyBase = input.number('SPY base', 1, { min: 1, max: 10, step: 1 });
const spyColor = input.color('SPY color', '#ff00ff');
const spyOffset = input.number('SPY left', 50, { min: 0, step: 10 });
const spyStyle = input.select('SPY style', 'Dashed', ['Solid', 'Dashed', 'Dotted', 'None']);

const enableSpx = input.boolean('SPX on', false);
const spxMult = input.number('SPX increment', 10, { min: 0.1, step: 5 });
const spxBase = input.number('SPX base', 10, { min: 1, max: 10, step: 1 });
const spxColor = input.color('SPX color', '#ffff00');
const spxOffset = input.number('SPX left', 100, { min: 0, step: 10 });
const spxStyle = input.select('SPX style', 'Dashed', ['Solid', 'Dashed', 'Dotted', 'None']);

const enableEs = input.boolean('ES on', false);
const esMult = input.number('ES increment', 10, { min: 0.25, step: 5 });
const esBase = input.number('ES base', 10, { min: 1, max: 10, step: 1 });
const esColor = input.color('ES color', '#ff9900');
const esOffset = input.number('ES left', 150, { min: 0, step: 10 });
const esStyle = input.select('ES style', 'Dashed', ['Solid', 'Dashed', 'Dotted', 'None']);

const levelsEachSide = input.number('# levels +/-', 10, { min: 0, max: 10, step: 1 });
const updateFreq = input.select('Update', 'Every tick', ['Every tick', 'Per Candle Close']);
const showTable = input.boolean('Table', true);
const tableFontSize = input.select('Table size', 'Normal', ['Auto', 'Tiny', 'Small', 'Normal', 'Large']);
const showChange = input.boolean('Show chg', true);

const SPX_SYMBOL = '$SPX';
const ES_SYMBOL = 'ES1!';
const THEME_BG = 'var(--background-color)';
const THEME_TEXT = 'var(--text-color)';
const THEME_ACCENT = 'var(--text-accent-color)';
const THEME_BORDER = 'var(--border-color)';
const POSITIVE_COLOR = '#15803d';
const NEGATIVE_COLOR = '#b91c1c';
const MAX_LEVELS_EACH_SIDE = 10;
const barCount = close.length;
const activeIndex = Math.max(0, updateFreq === 'Per Candle Close' && barCount > 1 ? barCount - 2 : barCount - 1);
const useExtSession = current.is_ext_hours === true || (constants.session && constants.ext_session && constants.session.lengthMinutes === constants.ext_session.lengthMinutes);

const needSpy = enableSpy || showTable;
const needSpx = enableSpx || showTable;
const needEs = enableEs || showTable;

const [spyData, spxData, esData] = await Promise.all([
	needSpy ? getSymbolData('SPY') : null,
	needSpx ? getSymbolData(SPX_SYMBOL) : null,
	needEs ? getSymbolData(ES_SYMBOL) : null
]);

const chartClose = valueAt(close, activeIndex);
const regularChartClose = latestRegularChartClose();

drawConvertedLevels('SPY', 'SPY', enableSpy, spyData && spyData.price, anchoredBase(spyData && spyData.price, spyMult, spyBase), spyMult, regularChartClose, spyOffset, spyColor, spyStyle);
drawConvertedLevels('SPX', 'SPX', enableSpx, spxData && spxData.price, anchoredBase(spxData && spxData.price, spxMult, spxBase), spxMult, regularChartClose, spxOffset, spxColor, spxStyle);
drawConvertedLevels('ES', 'ES1!', enableEs, esData && esData.price, anchoredBase(esData && esData.price, esMult, esBase), esMult, chartClose, esOffset, esColor, esStyle);

const esPrevClose = showTable && showChange ? await getPriorRegularClose(ES_SYMBOL) : null;
const esPct = showChange ? pctChange(esData && esData.price, esPrevClose) : null;
const tableRows = showTable ? [
	tableHeader(),
	tableRow('SPY', spyData && spyData.price, null),
	tableRow('SPX', spxData && spxData.price, null),
	tableRow('ES1!', esData && esData.price, esPct)
] : [];
// Theme-aware table colors keep the overlay readable in both light and dark TrendSpider themes.
paint_overlay('SPY SPX ES Prices', { position: 'top_right', order: 'above_all' }, {
	background: THEME_BG,
	border: `solid ${THEME_BORDER} 1px`,
	color: THEME_TEXT,
	padding: 6,
	fontSize: fontSize(tableFontSize),
	rows: tableRows
});

function getLineStyle(style) {
	if (style === 'Solid') return 'line';
	if (style === 'Dotted') return 'dotted';
	if (style === 'Dashed') return 'dotted';
	return null;
}

function anchoredBase(price, multiplier, base) {
	if (!isNum(price) || !isNum(multiplier) || multiplier <= 0 || !isNum(base)) return null;
	const localBase = Math.floor(price / 10) * 10 + base;
	const kRaw = (price - localBase) / multiplier;
	const k = Math.round(kRaw);
	return localBase + k * multiplier;
}

function buildConvertedLevels(sourceLabel, enabled, sourcePrice, basePrice, multiplier, chartPrice) {
	const side = Math.min(MAX_LEVELS_EACH_SIDE, Math.max(0, Math.round(levelsEachSide)));
	const valid = enabled && isNum(sourcePrice) && sourcePrice !== 0 && isNum(basePrice) && isNum(multiplier) && isNum(chartPrice);
	const levels = [];
	for (let slot = 0; slot <= MAX_LEVELS_EACH_SIDE * 2; slot += 1) {
		const step = levelStep(slot);
		const active = valid && Math.abs(step) <= side;
		const source = active ? basePrice + step * multiplier : null;
		const value = active ? source * (chartPrice / sourcePrice) : null;
		levels.push({ source, value, text: active && isNum(value) ? `${sourceLabel} ${formatPrice(source)}` : '-' });
	}
	return levels;
}

function drawConvertedLevels(id, sourceLabel, enabled, sourcePrice, basePrice, multiplier, chartPrice, offsetBars, color, styleName) {
	const style = getLineStyle(styleName);
	const levels = buildConvertedLevels(sourceLabel, enabled, sourcePrice, basePrice, multiplier, chartPrice);
	const labelIndex = Math.max(0, activeIndex - Math.round(offsetBars));
	levels.forEach((level, slot) => {
		const visible = enabled && isNum(level.value);
		const levelSeries = visible ? horizontal_line(level.value) : series_of(null);
		const ref = paint(levelSeries, { name: `${id} Level ${slot + 1}`, color: style ? color : 'rgba(0,0,0,0)', style: style || 'line', thickness: 1, ignoreWhenScaling: true, editorHidden: true, hideInLegend: true, hideInScriptEditor: true });
		paint_label_at_line(ref, labelIndex, level.text, labelOptions(color));
	});
}

function levelStep(slot) {
	if (slot === 0) return 0;
	if (slot <= MAX_LEVELS_EACH_SIDE) return slot;
	return -(slot - MAX_LEVELS_EACH_SIDE);
}

function formatPrice(value) {
	if (!isNum(value)) return 'n/a';
	const decimals = Math.abs(value) >= 100 ? 2 : 4;
	return Number(value.toFixed(decimals)).toString();
}

function formatPercent(value) {
	if (!isNum(value)) return '';
	return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

async function getSymbolData(symbol) {
	if (!symbol) return null;
	if (sameTicker(symbol, current.ticker)) return { symbol, price: valueAt(close, activeIndex), close };
	const data = await requestHistory(symbol, current.resolution, { ext_session: useExtSession });
	if (!data) return null;
	const landed = interpolate_sparse_series(land_points_onto_series(data.time, data.close, time, 'ge'), 'constant');
	return { symbol, price: valueAt(landed, activeIndex), close: landed, raw: data };
}

async function requestHistory(symbol, resolution, options = {}) {
	try {
		const data = await request.history(symbol, resolution, options);
		if (!data || data.error || !Array.isArray(data.close)) {
			console.warn(`No usable data for ${symbol}: ${data && data.error ? data.error : 'unknown error'}`);
			return null;
		}
		return data;
	} catch (e) {
		console.warn(`Request failed for ${symbol}: ${e}`);
		return null;
	}
}

async function getPrevDailyClose(symbol) {
	const data = await requestHistory(symbol, 'D');
	return data && data.close.length > 1 ? data.close[data.close.length - 2] : null;
}

async function getPriorRegularClose(symbol) {
	const data = await requestHistory(symbol, '30', { ext_session: true });
	if (data) {
		const byDate = {};
		const order = [];
		for (let i = 0; i < data.time.length; i += 1) {
			if (data.time[i] > time[activeIndex] || !isRegularSessionTime(data.time[i])) continue;
			const key = nyDateKey(data.time[i]);
			if (!(key in byDate)) order.push(key);
			byDate[key] = data.close[i];
		}
		if (order.length > 1) return byDate[order[order.length - 2]];
	}
	return getPrevDailyClose(symbol);
}

function latestRegularChartClose() {
	for (let i = activeIndex; i >= 0; i -= 1) if (isRegularSessionTime(time[i]) && isNum(close[i])) return close[i];
	return chartClose;
}

function isRegularSessionTime(ts) {
	const p = time_of(ts);
	const hours = p.hours || p.hour || 0;
	const minutes = p.minutes || p.minute || 0;
	const weekday = p.weekday || p.dayOfWeek || p.day_of_week || '';
	const isWeekend = weekday === 'Sat' || weekday === 'Sun' || weekday === 0 || weekday === 6 || weekday === 7;
	const mins = hours * 60 + minutes;
	return !isWeekend && mins >= 570 && mins < 960;
}

function nyDateKey(ts) {
	const dayBar = bar_at(ts, 'D');
	return dayBar && dayBar.session ? String(dayBar.session) : String(ts);
}

function tableHeader() {
	const cells = [tableCell('Symbol', THEME_ACCENT, true), tableCell('Price', THEME_ACCENT, true), tableCell(showChange ? 'Change' : '', THEME_ACCENT, true)];
	return { cells };
}

function tableRow(symbol, price, pct) {
	const changeColor = !isNum(pct) ? THEME_TEXT : pct >= 0 ? POSITIVE_COLOR : NEGATIVE_COLOR;
	return { cells: [tableCell(symbol, THEME_TEXT, false), tableCell(formatPrice(price), THEME_TEXT, true), tableCell(showChange ? formatPercent(pct) : '', changeColor, true)] };
}

function tableCell(text, color, bold) {
	return { text, color, padding: 4, fontWeight: bold ? 'bold' : 'normal', background: 'transparent' };
}

function fontSize(label) {
	return { Tiny: '10px', Small: '11px', Normal: '12px', Large: '14px' }[label] || '12px';
}

function labelOptions(color) {
	return { color, background_color: 'rgba(128,128,128,0)', border_color: color, border_width: 1, border_radius: 3 };
}

function pctChange(now, prev) {
	return isNum(now) && isNum(prev) && prev !== 0 ? (now - prev) / prev * 100 : null;
}

function valueAt(series, index) {
	if (!Array.isArray(series)) return null;
	for (let i = Math.min(index, series.length - 1); i >= 0; i -= 1) if (isNum(series[i])) return series[i];
	return null;
}

function labelSymbol(symbol) {
	const s = String(symbol || '').trim();
	return s.includes(':') ? s.split(':').pop() : s;
}

function normTicker(symbol) {
	return labelSymbol(symbol).replace(/^$/, '').toUpperCase();
}

function sameTicker(a, b) {
	return normTicker(a) === normTicker(b);
}

function isNum(value) {
	return typeof value === 'number' && isFinite(value);
}
</code>