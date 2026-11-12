<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Squeeze Labels');

// Inputs for Bollinger Bands
const bbLength = input.number('Bollinger Length', 20, { min: 1 });
const bbMultiplier = input.number('Bollinger Multiplier', 2, { min: 0.1 });

// Inputs for Keltner Channel
const kcLength = input.number('Keltner Length', 20, { min: 1 });
const kcMultiplier = input.number('Keltner Multiplier', 2, { min: 0.1 });

// Calculate Bollinger Bands
const bbMiddle = sma(close, bbLength);
const bbDev = mult(stdev(close, bbLength), bbMultiplier);
const bbUpper = add(bbMiddle, bbDev);
const bbLower = sub(bbMiddle, bbDev);

// Calculate Keltner Channel
const kcMiddle = sma(close, kcLength);
const kcDev = mult(atr(14), kcMultiplier);
const kcUpper = add(kcMiddle, kcDev);
const kcLower = sub(kcMiddle, kcDev);

// Determine squeeze conditions
const mySqueezeCondition = for_every(bbUpper, bbLower, kcUpper, kcLower, 
    (_bbUp, _bbLow, _kcUp, _kcLow) => {
        if (_bbUp < _kcUp && _bbLow > _kcLow) {
            return '🍋'; // Lemon emoji for squeeze
        } else if (_bbUp > _kcUp && _bbLow < _kcLow) {
            return '🧃'; // Beverage box emoji for reverse squeeze
        }
        return null;
    }
);

// Function to remove consecutive duplicates
const removeDuplicates = (arr) => {
    return arr.map((value, index, array) => {
        if (index === 0 || value !== array[index - 1]) {
            return value;
        }
        return null;
    });
};

// Remove consecutive duplicates
const myUniqueCondition = removeDuplicates(mySqueezeCondition);

// Paint labels
paint(myUniqueCondition, {
    style: 'labels_above',
    name: 'Squeeze Indicator',
});</code>