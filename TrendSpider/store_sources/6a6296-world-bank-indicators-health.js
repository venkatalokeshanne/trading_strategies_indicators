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
const validIndicatorIds = ["SH.ALC.PCAP.FE.LI","SH.ALC.PCAP.LI","SH.ALC.PCAP.MA.LI","SH.ANM.CHLD.ZS","SH.ANM.ALLW.ZS","SH.DTH.INJR.ZS","SH.ANM.NPRG.ZS","SH.DTH.COMM.ZS","SH.DTH.IMRT.MA","SH.DTH.IMRT.FE","SH.DTH.IMRT","SH.DTH.MORT","SH.DTH.MORT.FE","SH.DTH.MORT.MA","SH.DTH.NCOM.ZS","SH.DTH.NMRT","SH.DTH.STLB","SH.DYN.AIDS.FE.ZS","SH.DYN.MORT","SH.DYN.MORT.FE","SH.DYN.MORT.MA","SH.DYN.NCOM.FE.ZS","SH.DYN.NCOM.MA.ZS","SH.DYN.NCOM.ZS","SH.DYN.NMRT","SH.DYN.STLB","SH.H2O.BASW.RU.ZS","SH.H2O.BASW.UR.ZS","SH.H2O.BASW.ZS","SH.H2O.SMDW.UR.ZS","SH.H2O.SMDW.ZS","SH.IMM.HEPB","SH.IMM.IDPT","SH.IMM.MEAS","SH.IMM.MEA2","SH.MED.BEDS.ZS","SH.MED.NUMW.P3","SH.MED.PHYS.ZS","SH.MED.SAOP.P5","SH.MMR.RISK","SH.MMR.RISK.ZS","SH.MMR.DTHS","SH.PRG.ANEM","SH.PRV.SMOK","SH.PRV.SMOK.FE","SH.PRV.SMOK.MA","SH.SGR.PROC.P5","SH.SGR.CRSK.ZS","SH.SGR.IRSK.ZS","SH.STA.AIRP.FE.P5","SH.STA.AIRP.MA.P5","SH.STA.AIRP.P5","SH.STA.BASS.UR.ZS","SH.STA.BASS.RU.ZS","SH.STA.BASS.ZS","SH.STA.BFED.ZS","SH.STA.BRTC.ZS","SH.STA.BRTW.ZS","SH.STA.DIAB.ZS","SH.STA.MALN.FE.ZS","SH.STA.MALN.MA.ZS","SH.STA.MMRT","SH.STA.MMRT.NE","SH.STA.ODFC.RU.ZS","SH.STA.MALN.ZS","SH.STA.ODFC.UR.ZS","SH.STA.ODFC.ZS","SH.STA.OWGH.FE.ZS","SH.STA.OWGH.MA.ZS","SH.STA.OWGH.ME.ZS","SH.STA.POIS.P5","SH.STA.OWGH.ZS","SH.STA.POIS.P5.MA","SH.STA.POIS.P5.FE","SH.STA.SMSS.ZS","SH.STA.SMSS.UR.ZS","SH.STA.STNT.FE.ZS","SH.STA.STNT.MA.ZS","SH.STA.STNT.ME.ZS","SH.STA.STNT.ZS","SH.STA.SUIC.MA.P5","SH.STA.SUIC.FE.P5","SH.STA.SUIC.P5","SH.STA.TRAF.P5","SH.STA.WASH.P5","SH.STA.WAST.FE.ZS","SH.STA.WAST.MA.ZS","SH.STA.WAST.ZS","SH.SVR.WAST.FE.ZS","SH.TBS.CURE.ZS","SH.SVR.WAST.MA.ZS","SH.SVR.WAST.ZS","SH.TBS.DTEC.ZS","SH.TBS.INCD","SH.UHC.NOP1.CG","SH.UHC.NOP1.ZG","SH.UHC.NOP1.TO","SH.UHC.NOP2.TO","SH.UHC.NOP2.ZG","SH.UHC.NOP2.CG","SH.UHC.OOPC.10.TO","SH.UHC.OOPC.25.TO","SH.XPD.CHEX.PC.CD","SH.XPD.CHEX.GD.ZS","SH.XPD.CHEX.PP.CD","SH.XPD.EHEX.PC.CD","SH.XPD.EHEX.PP.CD","SH.XPD.GHED.GD.ZS","SH.XPD.GHED.CH.ZS","SH.XPD.GHED.PC.CD","SH.XPD.GHED.GE.ZS","SH.XPD.EHEX.CH.ZS","SH.XPD.OOPC.CH.ZS","SH.XPD.OOPC.PC.CD","SH.XPD.GHED.PP.CD","SH.XPD.OOPC.PP.CD","SH.XPD.PVTD.CH.ZS","SH.XPD.PVTD.PC.CD","SH.XPD.PVTD.PP.CD","SM.POP.NETM","SM.POP.TOTL.ZS","SM.POP.TOTL","SN.ITK.DEFC.ZS","SN.ITK.MSFI.ZS","SN.ITK.SVFI.ZS","SP.DYN.AMRT.FE","SP.ADO.TFRT","SP.DYN.AMRT.MA","SP.DYN.CBRT.IN","SP.DYN.CDRT.IN","SP.DYN.CONM.ZS","SP.DYN.IMRT.IN","SP.DYN.IMRT.FE.IN","SP.DYN.CONU.ZS","SP.DYN.IMRT.MA.IN","SP.DYN.LE00.IN","SP.DYN.LE00.FE.IN","SP.DYN.TFRT.IN","SP.DYN.LE00.MA.IN","SP.DYN.TO65.FE.ZS","SP.DYN.TO65.MA.ZS","SP.POP.0004.FE.5Y","SP.POP.0014.FE.IN","SP.POP.0004.MA.5Y","SP.POP.0014.FE.ZS","SP.POP.0014.MA.IN","SP.POP.0014.TO","SP.POP.0014.TO.ZS","SP.POP.0509.FE.5Y","SP.POP.0509.MA.5Y","SP.POP.1014.MA.5Y","SP.POP.1519.MA.5Y","SP.POP.1519.FE.5Y","SP.POP.1564.FE.ZS","SP.POP.0014.MA.ZS","SP.POP.1564.FE.IN","SP.POP.1564.MA.IN","SP.POP.1564.MA.ZS","SP.POP.1564.TO","SP.POP.2024.FE.5Y","SP.POP.1564.TO.ZS","SP.POP.2529.FE.5Y","SP.POP.2529.MA.5Y","SP.POP.1014.FE.5Y","SP.POP.2024.MA.5Y","SP.POP.3034.FE.5Y","SP.POP.3034.MA.5Y","SP.POP.3539.FE.5Y","SP.POP.4044.MA.5Y","SP.POP.3539.MA.5Y","SP.POP.4549.MA.5Y","SP.POP.4549.FE.5Y","SP.POP.4044.FE.5Y","SP.POP.5054.FE.5Y","SP.POP.5054.MA.5Y","SP.POP.5559.MA.5Y","SP.POP.6064.FE.5Y","SP.POP.5559.FE.5Y","SP.POP.6064.MA.5Y","SP.POP.6569.MA.5Y","SP.POP.6569.FE.5Y","SP.POP.65UP.FE.IN","SP.POP.65UP.FE.ZS","SP.POP.65UP.TO","SP.POP.7074.FE.5Y","SP.POP.65UP.MA.IN","SP.POP.7074.MA.5Y","SP.POP.65UP.MA.ZS","SP.POP.7579.FE.5Y","SP.POP.80UP.FE","SP.POP.7579.MA.5Y","SP.POP.80UP.FE.5Y","SP.POP.80UP.MA.5Y","SP.POP.BRTH.MF","SP.POP.DPND","SP.POP.DPND.OL","SP.POP.GROW","SP.POP.DPND.YG","SP.POP.TOTL","SP.POP.TOTL.MA.IN","SP.POP.TOTL.FE.ZS","SP.POP.TOTL.MA.ZS","SP.POP.TOTL.FE.IN","SP.REG.BRTH.FE.ZS","SP.POP.65UP.TO.ZS","SP.REG.BRTH.MA.ZS","SP.REG.BRTH.ZS","SP.REG.DTHS.ZS","SP.UWT.TFRT"];
const data = await request.http(`https://api.worldbank.org/v2/topic/8/indicator?per_page=1000&format=json`);
const currentTopicIndicators = data[1].filter(indicator => validIndicatorIds.includes(indicator.id));
const indicatorTitles = currentTopicIndicators.map(indicator => indicator.name);
const currentIndicatorTitle = input.select('Indicator', indicatorTitles[0], indicatorTitles);
const currentIndicator = currentTopicIndicators.find(indicator => indicator.name == currentIndicatorTitle);
const indicatorId = currentIndicator.id;
const indicatorNote = (str => str.length > 80 ? str.slice(0, 80 - 3) + '...' : str)(currentIndicator.sourceNote);
describe_indicator(`World Bank Indicators - Health`, 'lower', { citation: indicatorNote, shortName: `WBI Health` });
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