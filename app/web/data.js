// Sample values, shown until the pipeline has written results to outputs/.
// app/dashboard.py builds the same shape from the real files and app.py
// injects it as window.TMINUS_DATA.
//
//   world      size of the map image in units, and metres per unit
//   scenes     one per radar date, oldest first. img is null here: the sample
//              scene is drawn by scene.js instead
//   alerts     in priority order. series is the brightness (dB) at the alert
//              in each scene. The sample places alerts with x, y on the drawn
//              scene; real alerts are placed from lon, lat and bounds
//   crackdown  rows are scene intervals (start, end) or labelled bars
//   accuracy   tables of hits, misses and false alarms per detector
window.TMINUS_SAMPLE = {
  sample: true,
  sensor: "RADARSAT-2 · Extra-Fine · HH · Ascending",
  credit: "",
  place: "La Pampa, Madre de Dios",
  facts: [
    { value: "92%", text: "drop in clearing in La Pampa after Operation Mercury began, Feb 2019" },
    { value: "900 ha", text: "cleared in La Pampa between February and June 2018" },
    { value: "24 days", text: "between RADARSAT-2 passes over the same spot" }
  ],
  sources: "Sources: MAAP #104; CSA, RADARSAT-2 Tropical Forests dataset",
  world: { w: 1000, h: 860, m_per_unit: 20 },
  bounds: null,
  la_pampa: null,
  drop_db: 3,
  scenes: [
    { date: "2015-08-09", img: null },
    { date: "2018-08-11", img: null },
    { date: "2021-08-14", img: null },
    { date: "2024-08-10", img: null }
  ],
  overlay: null,
  optical: null,
  alerts: [
    { id: "MDD-0142", type: "pond", area_ha: 18.4, confidence: "high", in_buffer: true, in_indigenous: false, dist_road_m: 2300, dist_river_m: 200, priority: 86.5, first_seen: "2021-08-14", x: 700, y: 705, series: [-7.4, -7.1, -17.0, -17.6] },
    { id: "MDD-0098", type: "pond", area_ha: 21.3, confidence: "high", in_buffer: false, in_indigenous: false, dist_road_m: 1100, dist_river_m: 3400, priority: 84.0, first_seen: "2018-08-11", x: 300, y: 690, series: [-7.1, -17.3, -17.9, -16.8] },
    { id: "MDD-0101", type: "pond", area_ha: 17.8, confidence: "high", in_buffer: true, in_indigenous: false, dist_road_m: 1800, dist_river_m: 3900, priority: 82.5, first_seen: "2018-08-11", x: 215, y: 735, series: [-7.6, -16.7, -17.2, -17.5] },
    { id: "MDD-0139", type: "pond", area_ha: 16.9, confidence: "high", in_buffer: false, in_indigenous: false, dist_road_m: 4100, dist_river_m: 100, priority: 78.0, first_seen: "2021-08-14", x: 806, y: 216, series: [-7.0, -7.3, -15.8, -16.4] },
    { id: "MDD-0171", type: "pond", area_ha: 11.2, confidence: "high", in_buffer: false, in_indigenous: false, dist_road_m: 5200, dist_river_m: 1900, priority: 74.0, first_seen: "2024-08-10", x: 880, y: 520, series: [-7.3, -7.0, -7.4, -16.3] },
    { id: "MDD-0176", type: "bare", area_ha: 8.5, confidence: "high", in_buffer: true, in_indigenous: false, dist_road_m: 4700, dist_river_m: 2400, priority: 73.5, first_seen: "2024-08-10", x: 905, y: 730, series: [-6.9, -7.2, -7.0, -13.0] },
    { id: "MDD-0104", type: "bare", area_ha: 14.2, confidence: "high", in_buffer: false, in_indigenous: false, dist_road_m: 600, dist_river_m: 2800, priority: 71.0, first_seen: "2018-08-11", x: 370, y: 655, series: [-6.9, -13.3, -13.8, -13.1] },
    { id: "MDD-0151", type: "bare", area_ha: 12.7, confidence: "high", in_buffer: false, in_indigenous: false, dist_road_m: 3600, dist_river_m: 600, priority: 69.0, first_seen: "2021-08-14", x: 650, y: 178, series: [-6.8, -7.1, -13.7, -14.0] },
    { id: "MDD-0147", type: "pond", area_ha: 7.2, confidence: "medium", in_buffer: true, in_indigenous: false, dist_road_m: 2900, dist_river_m: 300, priority: 61.0, first_seen: "2021-08-14", x: 627, y: 772, series: [-7.9, -7.6, -15.3, -15.9] },
    { id: "MDD-0093", type: "pond", area_ha: 9.6, confidence: "medium", in_buffer: false, in_indigenous: false, dist_road_m: 3200, dist_river_m: 100, priority: 52.0, first_seen: "2018-08-11", x: 250, y: 262, series: [-7.8, -16.1, -16.6, -15.9] },
    { id: "MDD-0155", type: "clearing", area_ha: 5.8, confidence: "medium", in_buffer: false, in_indigenous: false, dist_road_m: 3300, dist_river_m: 800, priority: 47.0, first_seen: "2021-08-14", x: 560, y: 262, series: [-7.2, -7.4, -11.1, -11.5] },
    { id: "MDD-0168", type: "clearing", area_ha: 6.0, confidence: "medium", in_buffer: false, in_indigenous: false, dist_road_m: 400, dist_river_m: 3100, priority: 45.0, first_seen: "2024-08-10", x: 480, y: 520, series: [-7.6, -7.3, -7.5, -11.4] },
    { id: "MDD-0161", type: "bare", area_ha: 3.9, confidence: "medium", in_buffer: false, in_indigenous: false, dist_road_m: 4400, dist_river_m: 1200, priority: 41.0, first_seen: "2021-08-14", x: 742, y: 318, series: [-7.5, -7.2, -12.7, -12.9] },
    { id: "MDD-0107", type: "clearing", area_ha: 4.4, confidence: "medium", in_buffer: false, in_indigenous: false, dist_road_m: 4000, dist_river_m: 900, priority: 38.0, first_seen: "2018-08-11", x: 150, y: 300, series: [-7.3, -10.9, -11.2, -10.6] },
    { id: "MDD-0158", type: "clearing", area_ha: 3.1, confidence: "medium", in_buffer: false, in_indigenous: false, dist_road_m: 1400, dist_river_m: 2600, priority: 34.0, first_seen: "2021-08-14", x: 120, y: 420, series: [-7.7, -7.5, -11.0, -10.8] },
    { id: "MDD-0179", type: "clearing", area_ha: 2.7, confidence: "medium", in_buffer: false, in_indigenous: false, dist_road_m: 2200, dist_river_m: 3600, priority: 31.0, first_seen: "2024-08-10", x: 62, y: 600, series: [-7.1, -7.4, -7.2, -10.3] }
  ],
  crackdown: {
    event: "Operation Mercury",
    date: "2019-02-19",
    unit: "ha per year",
    rows: [
      { label: "'14", phase: "before", inside: 380, outside: 300 },
      { label: "'15", phase: "before", inside: 520, outside: 340 },
      { label: "'16", phase: "before", inside: 610, outside: 360 },
      { label: "'17", phase: "before", inside: 760, outside: 410 },
      { label: "'18", phase: "before", inside: 940, outside: 480 },
      { label: "'19", phase: "after", inside: 140, outside: 560 },
      { label: "'20", phase: "after", inside: 60, outside: 640 },
      { label: "'21", phase: "after", inside: 40, outside: 720 },
      { label: "'22", phase: "after", inside: 30, outside: 780 },
      { label: "'23", phase: "after", inside: 25, outside: 760 },
      { label: "'24", phase: "after", inside: 20, outside: 730 }
    ],
    // average hectares per month
    summary: { before: { inside: 53.5, outside: 31.5 }, after: { inside: 4.4, outside: 58.2 } },
    amw: null
  },
  accuracy: {
    tables: [
      {
        title: "Points checked by eye",
        unit: "points",
        note: "60 points we labelled by eye on Sentinel-2 (30 mining, 30 not mining). The training labels are never used for this check.",
        rows: [
          { name: "Rule only", hits: 25, misses: 5, false_alarms: 10, precision: 25 / 35, recall: 25 / 30 },
          { name: "Model only", hits: 24, misses: 6, false_alarms: 7, precision: 24 / 31, recall: 24 / 30 },
          { name: "Both agree (high confidence)", hits: 23, misses: 7, false_alarms: 3, precision: 23 / 26, recall: 23 / 30, best: true }
        ]
      }
    ],
    comparison: null
  }
};
