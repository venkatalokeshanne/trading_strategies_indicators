<code x-ref="code" class="hljs" data-clipboard-text>const countries = {
  "Australia": "AUS",
  "Canada": "CAN",
  "China": "CHN",
  "European Union": "EUU",
  "Japan": "JPN",
  "Mexico": "MEX",
  "United Kingdom": "GBR",
  "United States": "USA",
  "World": "WLD"
};
const validIndicatorIds = ["EG.ELC.ACCS.RU.ZS","EG.ELC.ACCS.UR.ZS","EG.ELC.FOSL.ZS","EG.ELC.LOSS.ZS","EG.ELC.ACCS.ZS","EG.ELC.NGAS.ZS","EG.ELC.COAL.ZS","EG.ELC.HYRO.ZS","EG.ELC.NUCL.ZS","EG.ELC.PETR.ZS","EG.ELC.RNEW.ZS","EG.EGY.PRIM.PP.KD","EG.ELC.RNWX.KH","EG.ELC.RNWX.ZS","EG.FEC.RNEW.ZS","EG.GDP.PUSE.KO.PP","EG.IMP.CONS.ZS","EG.GDP.PUSE.KO.PP.KD","EG.USE.COMM.FO.ZS","EG.USE.COMM.GD.PP.KD","EG.USE.COMM.CL.ZS","EG.USE.CRNW.ZS","EG.USE.PCAP.KG.OE","EG.USE.ELEC.KH.PC","IC.FRM.BNKS.ZS","IC.ELC.DURS","IC.FRM.OUTG.ZS","NY.ADJ.DMIN.CD","NY.ADJ.DNGY.CD","NY.ADJ.DMIN.GN.ZS","NY.ADJ.DRES.GN.ZS","NY.ADJ.DNGY.GN.ZS","NY.GDP.MINR.RT.ZS","NY.GDP.PETR.RT.ZS","NY.GDP.NGAS.RT.ZS","NY.GDP.TOTL.RT.ZS","TM.VAL.FUEL.ZS.UN","TX.VAL.FUEL.ZS.UN","TM.VAL.MMTL.ZS.UN","TX.VAL.MMTL.ZS.UN"];
const data = await request.http(`https://api.worldbank.org/v2/topic/5/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Energy & Mining`, 'lower', { citation: indicatorNote, shortName: `WBI Energy` });
const country = input.select('Country', 'United States', Object.keys(countries));
const indicatorData = await request.http(`https://api.worldbank.org/v2/country/${countries[country]}/indicator/${indicatorId}?format=json&per_page=20000`);
assert(indicatorData[1] && indicatorData[1].some(d => d.value !== null && d.value !== ''), `The selected indicator doesn't return any data for "${country}".`);
const indicatorTimestamps = indicatorData[1].map(record => {
  const year = parseInt(record.date);
  const milliseconds = Date.UTC(year, 0, 1);
  return milliseconds / 1000;
}).reverse();
const indicatorValues = indicatorData[1].map(record => +record.value || null).reverse();
const lastIndexWithValue = indicatorValues.reduce((a, v, i) => a = v !== null ? i : a, 0);
const isLastValueOlderThanCandles = indicatorTimestamps[lastIndexWithValue] < time[0];
if (isLastValueOlderThanCandles) {
  indicatorTimestamps.push(time[0]);
  indicatorValues.push(indicatorValues[lastIndexWithValue]);
}
const indicatorLine = interpolate_sparse_series(land_points_onto_series(indicatorTimestamps, interpolate_sparse_series(indicatorValues), time, 'ge'), 'constant');
paint(indicatorLine, 'Line', '#469e48');</code>