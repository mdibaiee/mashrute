import { buildGraph } from './graph-model.js';
import { localePath } from './locale.js';

// Editorial navigation periods, delimited by events already in the chronology.
// They organize the wiki; they are not additional claims of participation.
export const PERIODS = [
  { id: 'origins', en: 'Roots of change', fa: 'زمینه‌های انقلاب', years: 'Before 1905', yearsFa: 'پیش از ۱۹۰۵', color: '#9b6c2e', end: '1905-01-01',
    summary_en: 'Concessions, foreign pressure, reform, and the Tobacco Protest set the stage for the constitutional movement.',
    summary_fa: 'امتیازها، فشار خارجی، اصلاحات و جنبش تنباکو زمینه‌ساز جنبش مشروطه شدند.',
    landmarks: ['tobacco-protest-1891', 'shirazi-fatwa-1891', 'russian-loans-1900-1902'] },
  { id: 'awakening', en: 'The uprising', fa: 'خیزش مشروطه‌خواهی', years: '1905–1906', yearsFa: '۱۹۰۵–۱۹۰۶', color: '#b95b39', end: '1906-08-05',
    summary_en: 'Protests and sanctuary movements pressed the shah for a house of justice and constitutional government.',
    summary_fa: 'اعتراض‌ها و بست‌نشینی‌ها شاه را برای تأسیس عدالت‌خانه و حکومت مشروطه تحت فشار گذاشتند.',
    landmarks: ['british-legation-bast-1906', 'bast-shah-abd-al-azim-1905', 'quchan-girls-sold-1905'] },
  { id: 'parliament', en: 'First Majlis', fa: 'مجلس اول', years: '1906–June 1908', yearsFa: '۱۹۰۶–ژوئن ۱۹۰۸', color: '#277d72', end: '1908-06-23',
    summary_en: 'The constitutional decree and First Majlis opened a struggle over law, representation, and the limits of royal power.',
    summary_fa: 'فرمان مشروطیت و مجلس اول میدان کشمکش بر سر قانون، نمایندگی و حدود قدرت سلطنت را گشودند.',
    landmarks: ['first-majlis-opens-1906', 'constitutional-decree-1906', 'supplementary-laws-ratified-1907'] },
  { id: 'resistance', en: 'Coup & resistance', fa: 'کودتا و مقاومت', years: 'June 1908–July 1909', yearsFa: 'ژوئن ۱۹۰۸–ژوئیه ۱۹۰۹', color: '#a03d62', end: '1909-07-16',
    summary_en: 'The bombardment of the Majlis was followed by repression, resistance in Tabriz, and advances from Gilan and Isfahan.',
    summary_fa: 'به توپ بستن مجلس با سرکوب، مقاومت تبریز و پیشروی نیروها از گیلان و اصفهان دنبال شد.',
    landmarks: ['bombardment-of-the-majlis-1908', 'azerbaijan-civil-war-1908', 'revolutionaries-take-rasht-1909'] },
  { id: 'restoration', en: 'Return of the Majlis', fa: 'بازگشت مشروطه', years: 'July 1909–1911', yearsFa: 'ژوئیه ۱۹۰۹–۱۹۱۱', color: '#425da3', end: '1912-01-01',
    summary_en: 'The reconquest of Tehran restored the constitution. The Second Majlis faced factional struggles and mounting foreign intervention.',
    summary_fa: 'فتح تهران مشروطه را بازگرداند. مجلس دوم با کشمکش جناح‌ها و مداخلهٔ فزایندهٔ قدرت‌های خارجی روبه‌رو شد.',
    landmarks: ['reconquest-of-tehran-1909', 'second-majlis-opens-1909', 'first-russian-ultimatum-1911'] },
  { id: 'aftermath', en: 'Aftermath', fa: 'پیامدهای انقلاب', years: 'After 1911', yearsFa: 'پس از ۱۹۱۱', color: '#776099', end: '9999',
    summary_en: 'Later events and the lives of the revolution’s participants extend beyond the dissolution of the Second Majlis.',
    summary_fa: 'رویدادهای بعدی و زندگی کنشگران انقلاب از انحلال مجلس دوم فراتر می‌رود.',
    landmarks: ['death-sattar-khan-1914'] },
  { id: 'context', en: 'Wider context', fa: 'چهره‌ها و زمینه‌ها', years: 'Across periods', yearsFa: 'فراتر از دوره‌ها', color: '#64748b',
    summary_en: 'People, groups, and cited scholars without a dated connection in the current dataset. Their links to the revolution are editorial context, not an invented event or date.',
    summary_fa: 'اشخاص، گروه‌ها و پژوهشگران مورد استناد که در داده‌های فعلی پیوند تاریخ‌داری ندارند. پیوندشان با انقلاب برای سامان‌دهی مطالب است و رویداد یا تاریخ تازه‌ای را ادعا نمی‌کند.',
    landmarks: [] },
];

export function eventPeriod(event) {
  // This range starts in an unspecified part of June. Its recorded summary
  // explicitly places the siege after the coup; June 1 would misclassify it.
  if (event.id === 'azerbaijan-civil-war-1908') return 'resistance';
  const date = (event.date_sort || (event.date_g_year ? `${event.date_g_year}-01-01` : ''))
    .replace(/-00/g, '-01');
  return date ? PERIODS.find((p) => p.end && date < p.end)?.id || 'aftermath' : 'context';
}

export function buildHistoryGraph(input, locale = 'fa', base = '') {
  const fa = locale === 'fa';
  const graph = buildGraph(input, locale, base);
  const byId = new Map(graph.nodes.map((n) => [n.data.id, n.data]));
  const votes = new Map(graph.nodes.map((n) => [n.data.id, new Map()]));
  const counts = new Map(PERIODS.map((p) => [p.id, { person: 0, group: 0, event: 0 }]));
  const eventById = new Map(input.events.map((e) => [e.id, e]));
  const vote = (id, era, weight = 1) => {
    if (!votes.has(id)) return;
    const periods = votes.get(id);
    periods.set(era, (periods.get(era) || 0) + weight);
  };
  for (const event of input.events) {
    const era = eventPeriod(event);
    vote(`event:${event.id}`, era);
    Object.assign(byId.get(`event:${event.id}`), { date: event.date_sort, significance: event.significance });
  }
  for (const { data: edge } of graph.edges) {
    edge.organizing = false;
    const event = [edge.source, edge.target].find((id) => id.startsWith('event:'));
    if (event) vote(edge.source === event ? edge.target : edge.source, eventPeriod(eventById.get(event.slice(6))));
  }
  const direct = new Map([...votes].map(([id, value]) => [id, new Map(value)]));
  // A group foundation is a dated record, but birth/death is not evidence of
  // a person's political activity. Never use lifespan to date participation.
  for (const group of input.groups) {
    if (!votes.get(`group:${group.id}`).size && group.founded_g_year) {
      vote(`group:${group.id}`, eventPeriod({ date_g_year: group.founded_g_year }));
      byId.get(`group:${group.id}`).periodBasis = 'foundation';
    }
  }
  // Untimed affiliations provide context only, clearly disclosed in the panel.
  const affiliationVotes = new Map();
  for (const { data: edge } of graph.edges) {
    if (!edge.source.startsWith('person:') || !edge.target.startsWith('group:') || direct.get(edge.source).size) continue;
    if (!affiliationVotes.has(edge.source)) affiliationVotes.set(edge.source, new Map());
    for (const [era] of votes.get(edge.target)) {
      const values = affiliationVotes.get(edge.source);
      values.set(era, (values.get(era) || 0) + 1);
    }
  }
  for (const [id, values] of affiliationVotes) {
    if (values.size) {
      votes.set(id, values);
      byId.get(id).periodBasis = 'affiliation';
    }
  }
  for (const { data } of graph.nodes) {
    const values = votes.get(data.id);
    data.periods = PERIODS.filter((p) => values.has(p.id)).map((p) => p.id);
    if (!data.periods.length) data.periods = ['context'];
    data.primaryPeriod = data.periods.reduce((best, era) => (values.get(era) || 0) > (values.get(best) || 0) ? era : best);
    data.periodBasis ||= values.size ? 'event' : 'context';
    data.color = PERIODS.find((p) => p.id === data.primaryPeriod).color;
    data.landmark = PERIODS.some((p) => p.landmarks.includes(data.slug));
    data.size = 23 + Math.min(8, Math.sqrt(data.degree));
    data.periods.forEach((era) => counts.get(era)[data.kind]++);
  }
  const periods = PERIODS.map((p, i) => ({
    id: p.id, index: i + 1, label: fa ? p.fa : p.en, years: fa ? p.yearsFa : p.years,
    color: p.color, summary: p[fa ? 'summary_fa' : 'summary_en'], counts: counts.get(p.id),
    landmarks: p.landmarks.map((id) => `event:${id}`).filter((id) => byId.has(id)),
  }));
  graph.nodes.push({ data: {
    id: 'revolution', kind: 'root', label: fa ? 'انقلاب مشروطه' : 'Constitutional Revolution',
    meta: fa ? '۱۹۰۵–۱۹۱۱' : '1905–1911', color: '#263991', shape: 'round-rectangle',
    summary: fa ? 'از زمینه‌های خیزش تا مجلس، مقاومت و پیامدها؛ هر دوره را برای کشف اشخاص، گروه‌ها و رویدادهایش باز کنید.' : 'From the roots of the uprising to parliament, resistance, and its aftermath. Open a period to explore its people, groups, and events.',
    href: localePath('/', locale, base), size: 180,
  } });
  for (const p of periods) graph.nodes.push({ data: {
    id: `period:${p.id}`, kind: 'period', period: p.id, label: p.label, meta: p.years,
    summary: p.summary, color: p.color, shape: 'round-rectangle', size: 165,
  } });
  const organize = (source, target, type) => graph.edges.push({ data: {
    id: `context:${source}:${target}`, source, target, type, organizing: true, directed: false,
    arrow: 'none', label: fa ? 'پیوند زمینه‌ای' : 'Contextual connection',
  } });
  for (const p of periods) organize('revolution', `period:${p.id}`, 'period');
  for (const [id, data] of byId) for (const era of data.periods) organize(`period:${era}`, id, 'period_member');
  return { ...graph, periods, totalRecords: byId.size, historicalEdges: graph.edges.filter((e) => !e.data.organizing).length };
}
