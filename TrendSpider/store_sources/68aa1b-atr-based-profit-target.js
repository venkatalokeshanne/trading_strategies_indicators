<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('ATR-based Profit Target');

// Input parameters
const atrPeriod = input.number('ATR Period', 14, { min: 1 });
const atrMultiplier = input.number('ATR Multiplier', 1, { min: 0.1, step: 0.1 });

// Calculate ATR
const myAtr = atr(high, low, close, atrPeriod);

// Calculate the profit target
const profitTarget = for_every(close, myAtr, (_close, _atr) => _close + _atr * atrMultiplier);

// Paint the profit target line
paint(profitTarget, { 
    name: 'ATR Profit Target', 
    color: 'green', 
    style: 'line',
    lineWidth: 2
});
</code>