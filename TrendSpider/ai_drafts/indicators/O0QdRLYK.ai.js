describe_indicator('IFR Niveis Moveis', 'lower');

// ================================================================
//                         INPUTS
// ================================================================
const myPriceSource = input.select('Fonte de Dados', 'close', constants.price_source_options);
const myPeriodo = input.number('Periodo do IFR', 14, { min: 1 });
const myNivelSobreCompra = input.number('Nivel Sobrecompra', 70, { min: 1, max: 100 });
const myNivelSobreVenda = input.number('Nivel Sobrevenda', 30, { min: 1, max: 100 });
const myMediaCurta = input.number('Periodo Media Curta', 9, { min: 1 });
const myMediaLonga = input.number('Periodo Media Longa', 50, { min: 1 });
const myPeriodoLimites = input.number('Periodo Max Min IFR', 200, { min: 1 });
const myPorcentagem = input.number('Taxa Desconto Percent', 5, { min: 0, max: 100, step: 0.1 });
const myNiveisFixos = input.boolean('Mostrar Niveis Fixos', false);
const myColorirLinhaIFR = input.boolean('Colorir Linha IFR', true);
// shortened input name to fit platform's name length limit
const myCorFixaIFR = input.color('Cor Fixa IFR', 'blue');

// ================================================================
//               CALCULO DO IFR (RSI) - Wilder's method
// ================================================================
const myPrice = market[myPriceSource];
const myRsi = rsi(myPrice, myPeriodo);

// ================================================================
//               NIVEIS MOVEIS (Maximas/Minimas do IFR)
// ================================================================
const myIfrMax = highest(myRsi, myPeriodoLimites);
const myIfrMin = lowest(myRsi, myPeriodoLimites);
const myNivelCentral = div(add(myIfrMax, myIfrMin), 2);
const myNivelSup = sub(myIfrMax, mult(myNivelCentral, 2 * myPorcentagem / 100));
const myNivelInf = add(myIfrMin, mult(myNivelCentral, 2 * myPorcentagem / 100));

// ================================================================
//                        MEDIAS DO IFR
// ================================================================
const myMediaCurtaPlot = sma(myRsi, myMediaCurta);
const myMediaLongaPlot = sma(myRsi, myMediaLonga);

// ================================================================
//                     COR DO IFR PRINCIPAL
// ================================================================
const myCorIFRDinamica = for_every(myRsi, myNivelSup, myNivelInf, (_r, _sup, _inf) => {
	if (_r >= _sup) return 'red';
	if (_r <= _inf) return 'green';
	return 'blue';
});

const myCorIFR = myColorirLinhaIFR ? myCorIFRDinamica : for_every(myRsi, () => myCorFixaIFR);

// ================================================================
//                          PLOTAGENS
// ================================================================
// IFR principal (colorido dinamicamente)
paint(myRsi, { name: 'IFR', color: myCorIFR, thickness: 2 });

// Medias sobre o IFR
paint(myMediaCurtaPlot, { name: 'Media Curta', color: 'green', thickness: 1 });
paint(myMediaLongaPlot, { name: 'Media Longa', color: 'orange', thickness: 1 });

// Niveis moveis
paint(myNivelSup, { name: 'Nivel Sup Movel', color: 'red', style: 'line', thickness: 1 });
paint(myNivelInf, { name: 'Nivel Inf Movel', color: 'green', style: 'line', thickness: 1 });
paint(myNivelCentral, { name: 'Nivel Central', color: 'gray', style: 'line', thickness: 1 });

// Niveis fixos (exibidos apenas se myNiveisFixos = true, caso contrario series nula)
paint(myNiveisFixos ? horizontal_line(myNivelSobreCompra) : constants.empty_series, { name: 'Sobrecompra Fixo', color: 'red', style: 'dotted', thickness: 1 });
paint(myNiveisFixos ? horizontal_line(myNivelSobreVenda) : constants.empty_series, { name: 'Sobrevenda Fixo', color: 'green', style: 'dotted', thickness: 1 });
paint(myNiveisFixos ? horizontal_line(50) : constants.empty_series, { name: 'Nivel 50 Fixo', color: 'gray', style: 'dotted', thickness: 1 });

// ================================================================
//                     SINAIS PARA SCANNER/ALERTAS/ESTRATEGIA
// ================================================================
register_signal(for_every(myRsi, myNivelSup, (_r, _sup) => _r >= _sup), 'IFR Acima do Nivel Sup Movel');
register_signal(for_every(myRsi, myNivelInf, (_r, _inf) => _r <= _inf), 'IFR Abaixo do Nivel Inf Movel');
register_signal(for_every(myRsi, myMediaCurtaPlot, (_r, _m) => _r > _m), 'IFR Acima da Media Curta');
register_signal(for_every(myRsi, myMediaCurtaPlot, (_r, _m) => _r < _m), 'IFR Abaixo da Media Curta');
register_signal(for_every(myRsi, (_r) => _r >= myNivelSobreCompra), 'IFR Acima do Nivel Fixo Sobrecompra');
register_signal(for_every(myRsi, (_r) => _r <= myNivelSobreVenda), 'IFR Abaixo do Nivel Fixo Sobrevenda');