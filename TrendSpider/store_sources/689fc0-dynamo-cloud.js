<code x-ref="code" class="hljs" data-clipboard-text>// ░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓██████▓▒░░▒▓███████▓▒░░▒▓████████▓▒░       ░▒▓███████▓▒░▒▓████████▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓███████▓▒░ ░▒▓███████▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░             ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░        
//    ░▒▓█▓▒░   ░▒▓███████▓▒░░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓██████▓▒░         ░▒▓██████▓▒░░▒▓██████▓▒░ ░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓██████▓▒░ ░▒▓███████▓▒░ ░▒▓██████▓▒░  
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░                    ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░                    ░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░ 
//    ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓████████▓▒░      ░▒▓███████▓▒░░▒▓████████▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░                                                                                                                                                                      

describe_indicator('Dynamo Cloud', {decimals: 2});

// consts
const colorUp = '#60935D';
const colorDown = '#D35F70';
const colorCounterAbove = '#902737';
const colorCounterBelow = '#13471d';
const lengthShort = 9;
const lengthLong = 14;
const lengthBalance = 28;

// vars
const alphaShort = 2 / (lengthShort + 1);
const alphaLong = 2 / (lengthLong + 1);
const alphaBalance = 2 / (lengthBalance + 1);
const priceCmoShort = cmo(close, lengthShort);
const priceCmoLong = cmo(close, lengthLong);
const priceCmoBalance = cmo(close, lengthBalance);

const vidyaShort = for_every(close, priceCmoShort, (curPrice, cmoValue, prevValue) => {

	if (curPrice === null || cmoValue === null) {
		return null;
	}

	if (prevValue === null) {
		return curPrice;
	}

	const absCmo = Math.abs(cmoValue);
	return curPrice * alphaShort * absCmo + prevValue * (1 - alphaShort * absCmo);
});

const vidyaLong = for_every(close, priceCmoLong, (curPrice, cmoValue, prevValue) => {

	if (curPrice === null || cmoValue === null) {
		return null;
	}

	if (prevValue === null) {
		return curPrice;
	}

	const absCmo = Math.abs(cmoValue);
	return curPrice * alphaLong * absCmo + prevValue * (1 - alphaLong * absCmo);
});

const vidyaBalance = for_every(close, priceCmoBalance, (curPrice, cmoValue, prevValue) => {

	if (curPrice === null || cmoValue === null) {
		return null;
	}

	if (prevValue === null) {
		return curPrice;
	}

	const absCmo = Math.abs(cmoValue);
	return curPrice * alphaBalance * absCmo + prevValue * (1 - alphaBalance * absCmo);
});

const shortColors = for_every(vidyaShort, vidyaLong, vidyaBalance, (s, l, b) => s > l ? colorUp : colorDown);
const balanceColors = for_every(vidyaShort, vidyaLong, vidyaBalance, (s, l, b) => s > b ? colorCounterBelow : colorCounterAbove);

// plots
paint(vidyaShort, 'Short', shortColors);
paint(vidyaLong, 'Long', shortColors);
paint(vidyaBalance, 'Balance', balanceColors);

color_cloud(vidyaShort, vidyaLong, colorUp, colorDown, 'Up Trend', 'Down Trend');
color_cloud(vidyaBalance, vidyaLong, colorCounterAbove, colorCounterBelow, 'Counter Trend Down', 'Counter Trend Up');</code>