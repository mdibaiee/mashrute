import cytoscape from 'cytoscape';
import { NODE_TYPES, normalizeSearch } from './graph-model.js';
import { chooseLabels } from './graph-labels.js';

export function initGraph() {
  const root = document.querySelector('[data-graph]');
  if (!root) return;
  const fa = root.dataset.locale === 'fa';
  const t = (en, persian) => fa ? persian : en;
  const num = (n) => n.toLocaleString(fa ? 'fa-IR' : 'en');
  const el = (name) => root.querySelector(`[data-${name}]`);
  const canvas = el('canvas');
  const graph = JSON.parse(el('graph-data').textContent);
  const eras = new Map(graph.periods.map((p) => [p.id, p]));
  const enabled = new Set(Object.keys(NODE_TYPES));
  const mobile = () => canvas.clientWidth < 540;
  const periodName = (id) => eras.get(id)?.label || '';
  const measure = document.createElement('canvas').getContext('2d');
  const font = fa ? 'Gandom' : 'Open Sans';
  let mode = 'overview';
  let currentEra = null;
  let selected = null;
  let limit = 12;
  let hovered = null;
  let frame = null;
  let cy;
  const lighten = (hex) => {
    const rgb = hex.slice(1).match(/../g).map((s) => Math.round(parseInt(s, 16) * .08 + 255 * .92));
    return `rgb(${rgb.join(',')})`;
  };
  graph.nodes.forEach(({ data }) => {
    data.displayLabel = data.label;
    data.fill = data.kind === 'period' ? lighten(data.color) : data.color;
  });
  try {
    cy = cytoscape({
      container: canvas, elements: [...graph.nodes, ...graph.edges],
      layout: { name: 'preset', fit: false }, minZoom: .25, maxZoom: 3,
      boxSelectionEnabled: false, selectionType: 'single',
      style: [
        { selector: 'node', style: {
          shape: 'data(shape)', 'background-color': 'data(fill)', width: 28, height: 28,
          label: 'data(displayLabel)', color: '#202b48', 'font-family': `${font}, sans-serif`,
          'font-size': 12, 'text-valign': 'bottom', 'text-margin-y': 7,
          'text-opacity': 0, 'text-wrap': 'ellipsis', 'text-max-width': 145,
          'text-background-color': '#fbfcff', 'text-background-opacity': .94,
          'text-background-padding': '2px', 'text-background-shape': 'round-rectangle',
          'border-color': '#fff', 'border-width': 2, 'overlay-opacity': 0,
        } },
        { selector: 'node[kind="root"], node[kind="period"], node[kind="lane"]', style: {
          'text-opacity': 1, 'text-valign': 'center', 'text-margin-y': 0, 'text-wrap': 'wrap',
          'text-background-opacity': 0, 'border-color': 'data(color)', 'font-weight': 600,
        } },
        { selector: 'node[kind="root"]', style: { color: '#ffffff' } },
        { selector: 'node[kind="lane"]', style: { 'background-opacity': 0, 'border-width': 0, color: '#69738a' } },
        { selector: 'node.labelled', style: { 'text-opacity': 1 } },
        { selector: 'edge', style: {
          width: 1.4, 'line-color': '#7e8aa4', 'curve-style': 'bezier', opacity: .2,
          events: 'no',
          'overlay-opacity': 0, 'target-arrow-shape': 'data(arrow)', 'target-arrow-color': '#7e8aa4', 'arrow-scale': .8,
        } },
        { selector: 'edge[?organizing]', style: {
          'line-style': 'dashed', 'line-color': '#b3bcd0', width: 1.1, opacity: .65,
          'target-arrow-shape': 'none', 'curve-style': 'straight',
        } },
        { selector: 'edge.scene-edge', style: { opacity: .3 } },
        { selector: '.muted', style: { opacity: .23 } },
        { selector: 'node.chosen', style: { 'border-color': '#14234b', 'border-width': 3.5, 'z-index': 10 } },
        { selector: 'edge.active-edge', style: { 'line-color': '#354970', 'target-arrow-color': '#354970', opacity: 1, width: 2 } },
        { selector: '.hidden', style: { display: 'none' } },
      ],
    });
    el('loading').hidden = true;
  } catch (error) {
    el('loading').textContent = t('The graph could not open. Please reload.', 'شبکه نمایش داده نشد. صفحه را دوباره بارگذاری کنید.');
    console.error(error);
    return;
  }
  const records = cy.nodes().filter((n) => Boolean(n.data('periods')));
  cy.nodes().difference(records).ungrabify();
  const searchNames = new Map(records.map((n) => [n.id(), normalizeSearch(n.data('search'))]));
  const shown = () => cy.elements().not('.hidden');
  const isRecord = (n) => Boolean(NODE_TYPES[n.data('kind')]);
  const checks = [...root.querySelectorAll('[data-type]')];

  function truncate(text, width, size) {
    measure.font = `${size}px "${font}"`;
    if (measure.measureText(text).width <= width) return text;
    let result = text;
    while (result.length && measure.measureText(result + '…').width > width) result = result.slice(0, -1);
    return result + '…';
  }

  function updateTypography() {
    const zoom = cy.zoom();
    const obstacles = [];
    const candidates = [];
    const size = Math.max(10, Math.min(13, 12 * Math.sqrt(zoom)));
    const visible = cy.nodes().not('.hidden');
    cy.batch(() => {
      visible.forEach((n) => {
        const kind = n.data('kind');
        const anchor = !isRecord(n);
        const width = anchor ? (kind === 'root' ? 190 : kind === 'lane' ? 150 : 174) : Math.max(20, Math.min(34, n.data('size') * Math.sqrt(zoom)));
        const height = anchor ? (kind === 'root' ? 80 : kind === 'lane' ? 28 : 70) : width;
        const textSize = kind === 'root' ? 16 : anchor ? 12 : size;
        n.style({ width: width / zoom, height: height / zoom, 'font-size': textSize / zoom, 'text-max-width': (anchor ? width - 18 : 145) / zoom, 'text-margin-y': anchor ? 0 : 7 / zoom });
        const p = n.renderedPosition();
        obstacles.push({ id: n.id(), rect: { x: p.x - width / 2 - 2, y: p.y - height / 2 - 2, width: width + 4, height: height + 4 } });
        if (!anchor) {
          const text = truncate(n.data('label'), 145, size);
          n.data('displayLabel', text);
          const textWidth = measure.measureText(text).width + 6;
          candidates.push({ id: n.id(), priority: n.id() === selected?.id() ? 10000 : n.id() === hovered?.id() ? 9000 : n.data('landmark') ? 2000 : n.data('degree') || 0,
            rect: { x: p.x - textWidth / 2, y: p.y + height / 2 + 5, width: textWidth, height: size * 1.5 + 4 } });
        }
      });
      visible.removeClass('labelled');
      const labels = chooseLabels(candidates, obstacles, { width: cy.width(), height: cy.height() });
      labels.forEach((id) => cy.getElementById(id).addClass('labelled'));
    });
  }
  function scheduleTypography() {
    if (frame !== null) return;
    frame = requestAnimationFrame(() => { frame = null; updateTypography(); });
  }

  function row(node, text = '') {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    const mark = document.createElement('span');
    mark.className = `graph__shape graph__shape--${node.data('kind')}`;
    mark.style.backgroundColor = node.data('color');
    mark.setAttribute('aria-hidden', 'true');
    const body = document.createElement('span');
    const title = document.createElement('span');
    title.className = 'graph__row-label';
    title.textContent = node.data('label');
    body.append(title);
    if (text) {
      const meta = document.createElement('span');
      meta.className = 'graph__row-meta';
      meta.textContent = text;
      body.append(meta);
    }
    button.append(mark, body);
    button.addEventListener('click', () => inspect(node, true));
    li.append(button);
    return li;
  }

  function clearDetail() {
    selected = null;
    el('detail').hidden = true;
    el('intro').hidden = false;
  }
  function contextPanel(era) {
    const p = era ? eras.get(era) : null;
    el('intro-title').textContent = p ? p.label : t('Follow the revolution', 'مسیر انقلاب را دنبال کنید');
    el('intro-summary').textContent = p ? p.summary : cy.getElementById('revolution').data('summary');
    el('milestones').replaceChildren();
    el('milestones-title').hidden = !p || !p.landmarks.length;
    if (p) p.landmarks.forEach((id) => el('milestones').append(row(cy.getElementById(id), cy.getElementById(id).data('meta'))));
    el('intro-note').textContent = era === 'context'
      ? t('These entries lack a dated affiliation. They remain connected through the wiki’s context, with no invented participation.', 'این مدخل‌ها پیوند تاریخ‌داری ندارند و از راه زمینهٔ دانشنامه متصل می‌مانند؛ مشارکتی برایشان ساخته نشده است.')
      : era ? t('Connections are faintly visible. Hover or select an entry to highlight its recorded relationships. Events follow chronological order; people and groups are ranked by their connections.', 'پیوندها کم‌رنگ نمایش داده می‌شوند. برای برجسته کردن پیوندهای ثبت‌شده، روی مدخلی بروید یا آن را انتخاب کنید. رویدادها به ترتیب زمان و اشخاص و گروه‌ها بر پایهٔ شمار پیوندها مرتب‌اند.')
      : t('Shapes identify people, groups, and events. Colours identify historical periods. Dashed lines organise the history; solid lines show documented relationships.', 'شکل‌ها اشخاص، گروه‌ها و رویدادها را مشخص می‌کنند و رنگ‌ها نشان‌دهندهٔ دوره‌های تاریخی‌اند. خط‌چین‌ها تاریخ را سامان می‌دهند؛ خط‌های پیوسته پیوندهای ثبت‌شده را نشان می‌دهند.');
  }
  function caption() {
    const entities = cy.nodes().not('.hidden').filter(isRecord).length;
    el('stats').textContent = mode === 'overview'
      ? t(`${num(graph.totalRecords)} entries · ${num(graph.periods.length)} clusters`, `${num(graph.totalRecords)} مدخل · ${num(graph.periods.length)} خوشه`)
      : t(`${num(entities)} entries shown · drag to explore`, `${num(entities)} مدخل در نمایش · برای کاوش بکشید`);
    el('view-title').textContent = mode === 'overview' ? t('The revolution at a glance', 'انقلاب در یک نگاه') : mode === 'period' ? periodName(currentEra) : t('Connections', 'پیوندها');
    el('back').hidden = mode === 'overview';
    el('period-open').hidden = !selected;
    el('more').hidden = mode !== 'period' || !records.some((n) => enabled.has(n.data('kind')) && n.data('periods').includes(currentEra) && n.hasClass('hidden'));
    el('empty').hidden = mode === 'overview' || cy.nodes().not('.hidden').filter(isRecord).length > 0;
    root.dataset.mode = mode;
    root.dataset.period = currentEra || '';
    root.querySelectorAll('[data-era]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.era === currentEra)));
  }
  function hideAll() {
    hovered = null;
    el('tooltip').hidden = true;
    cy.remove('.scene-edge, node[kind="lane"]');
    records.removeStyle('background-color');
    cy.elements().addClass('hidden').removeClass('muted chosen active-edge');
  }
  function reveal(ids, position) {
    ids.forEach((id, i) => {
      const node = cy.getElementById(id);
      node.removeClass('hidden');
      if (position) node.position(position(node, i));
    });
  }
  function showEdges() {
    const highlighted = hovered || selected;
    cy.batch(() => {
      cy.edges().removeClass('active-edge');
      cy.edges().forEach((edge) => {
        const hidden = edge.source().hasClass('hidden') || edge.target().hasClass('hidden') ||
          edge.data('type') === 'period_member' && (mode === 'period' || mode === 'local' && edge.target().id() !== selected?.id());
        edge.toggleClass('hidden', hidden);
        if (!hidden && highlighted && (edge.source().id() === highlighted.id() || edge.target().id() === highlighted.id())) edge.addClass('active-edge');
      });
    });
    cy.nodes('.chosen').removeClass('chosen');
    if (selected) selected.addClass('chosen');
  }
  function fitView() {
    if (mode === 'overview' && mobile()) {
      cy.viewport({ zoom: .9, pan: { x: cy.width() / 2, y: 65 } });
    } else if (mode === 'period') {
      cy.viewport({ zoom: mobile() ? .8 : .95, pan: { x: cy.width() / 2, y: 48 } });
    } else {
      cy.fit(shown(), 70);
    }
    scheduleTypography();
  }
  function overview() {
    mode = 'overview'; currentEra = null; limit = 12;
    cy.minZoom(mobile() ? .7 : .45);
    clearDetail(); hideAll();
    const positions = [[-480,-310],[0,-310],[480,-310],[480,230],[0,230],[-480,230],[-630,-35]];
    reveal(['revolution'], () => ({ x: 0, y: mobile() ? 0 : -5 }));
    graph.periods.forEach((p, i) => {
      const [x, y] = mobile() ? [0, 160 + i * 140] : positions[i];
      const hub = cy.getElementById(`period:${p.id}`);
      reveal([hub.id()], () => ({ x, y }));
      hub.data('displayLabel', `${num(i + 1)} · ${p.label}\n${p.years}`);
      if (!mobile()) {
        const preview = p.landmarks.find((id) => enabled.has('event') && cy.getElementById(id).length);
        if (preview) reveal([preview], () => ({ x, y: y + 125 }));
      }
    });
    cy.getElementById('revolution').data('displayLabel', `${cy.getElementById('revolution').data('label')}\n${fa ? '۱۹۰۵–۱۹۱۱' : '1905–1911'}`);
    contextPanel(); showEdges(); caption(); fitView();
  }
  function ranked(era, kind) {
    return records.filter((n) => n.data('kind') === kind && n.data('periods').includes(era))
      .sort((a, b) => kind === 'event'
        ? (Number(b.data('landmark')) - Number(a.data('landmark')) || (a.data('significance') || 3) - (b.data('significance') || 3) || a.data('date').localeCompare(b.data('date')))
        : b.data('degree') - a.data('degree') || a.id().localeCompare(b.id()));
  }
  function sceneEdge(source, target, id) {
    cy.add({ group: 'edges', classes: 'scene-edge', data: { id: `scene:${id}`, source, target, organizing: true, arrow: 'none' } });
  }
  function periodView(era, preserve = false) {
    mode = 'period'; currentEra = era;
    cy.minZoom(.6);
    clearDetail(); hideAll();
    const p = eras.get(era);
    reveal(['revolution', `period:${era}`], (node) => ({ x: 0, y: node.id() === 'revolution' ? 0 : 145 }));
    cy.getElementById(`period:${era}`).data('displayLabel', `${p.label}\n${p.years}`);
    const columns = mobile() ? { person: -165, event: 0, group: 165 } : { person: -285, event: 0, group: 285 };
    Object.keys(columns).forEach((kind) => {
      if (!enabled.has(kind)) return;
      let nodes = ranked(era, kind).slice(0, limit);
      if (kind === 'event') nodes = nodes.sort((a, b) => a.data('date').localeCompare(b.data('date')));
      const lane = `lane:${kind}`;
      cy.add({ group: 'nodes', grabbable: false, data: { id: lane, kind: 'lane', label: `${NODE_TYPES[kind][fa ? 'fa' : 'en']} · ${num(ranked(era, kind).length)}`, displayLabel: `${NODE_TYPES[kind][fa ? 'fa' : 'en']} · ${num(ranked(era, kind).length)}`, color: p.color, fill: '#ffffff', shape: 'rectangle' }, position: { x: columns[kind], y: 235 } });
      sceneEdge(`period:${era}`, lane, kind);
      nodes.forEach((node, i) => {
        reveal([node.id()], () => ({ x: columns[kind], y: 305 + i * 90 }));
        node.style({ 'background-color': p.color });
        sceneEdge(lane, node.id(), node.id());
      });
    });
    contextPanel(era); showEdges(); caption();
    if (!preserve) fitView();
    scheduleTypography();
  }
  function localView(node) {
    mode = 'local'; currentEra = node.data('primaryPeriod');
    cy.minZoom(.6);
    hideAll();
    reveal(['revolution', `period:${currentEra}`, node.id()], (n) => ({ x: 0, y: n.id() === 'revolution' ? -200 : n.data('kind') === 'period' ? -65 : 85 }));
    const neighbors = node.connectedEdges().filter((e) => !e.data('organizing') && !e.hasClass('scene-edge')).connectedNodes().difference(node)
      .filter((n) => enabled.has(n.data('kind')));
    const columns = { person: -260, event: 0, group: 260 };
    Object.entries(columns).forEach(([kind, x]) => {
      const nodes = neighbors.filter((n) => n.data('kind') === kind).sort((a, b) => b.data('degree') - a.data('degree'));
      reveal(nodes.map((n) => n.id()), (n, i) => ({ x, y: 230 + i * 85 }));
    });
    // A neighbor's organizing path stays visible too, even when it belongs to
    // another era. Its sourced relationship to the selected record is solid.
    selected = node;
    showEdges(); caption();
    if (mobile()) cy.viewport({ zoom: .7, pan: { x: cy.width() / 2, y: 180 } });
    else cy.viewport({ zoom: .9, pan: { x: cy.width() / 2, y: 225 } });
    scheduleTypography();
  }

  function inspect(node, local = false) {
    if (!isRecord(node)) return;
    selected = node;
    enabled.add(node.data('kind'));
    checks.forEach((check) => { check.checked = enabled.has(check.value); });
    if (local || mode === 'overview' || node.hasClass('hidden')) localView(node);
    else { showEdges(); scheduleTypography(); }
    el('intro').hidden = true; el('detail').hidden = false;
    el('kind').textContent = NODE_TYPES[node.data('kind')][fa ? 'fa' : 'en'];
    el('title').textContent = node.data('label');
    el('meta').textContent = node.data('meta');
    el('summary').textContent = node.data('summary');
    el('record').href = node.data('href');
    el('period-memberships').replaceChildren();
    node.data('periods').forEach((era) => {
      const button = document.createElement('button'); button.type = 'button';
      button.textContent = periodName(era); button.style.borderColor = eras.get(era).color;
      button.addEventListener('click', () => { limit = 12; periodView(era); });
      el('period-memberships').append(button);
    });
    const basis = node.data('periodBasis');
    el('period-basis').textContent = basis === 'context' ? t('No dated affiliation is recorded. Connected here through the wiki’s wider context.', 'وابستگی تاریخ‌داری ثبت نشده است. این مدخل از راه زمینهٔ دانشنامه متصل است.')
      : basis === 'affiliation' ? t('Period placement comes from group affiliations; it does not date this person’s membership or prove event participation.', 'جای‌گذاری در دوره از وابستگی گروهی آمده است؛ تاریخ عضویت یا مشارکت در رویداد را ثابت نمی‌کند.')
      : basis === 'foundation' ? t('Period placement uses the recorded year of this group’s foundation.', 'جای‌گذاری در دوره بر پایهٔ سال ثبت‌شدهٔ تأسیس گروه است.')
      : t('Periods follow the dated events linked to this entry.', 'دوره‌ها بر پایهٔ رویدادهای تاریخ‌دارِ مرتبط با این مدخل‌اند.');
    const connected = new Map();
    node.connectedEdges().filter((e) => !e.data('organizing')).forEach((edge) => {
      const other = edge.source().id() === node.id() ? edge.target() : edge.source();
      let label = edge.data('label');
      if (edge.data('directed') && edge.target().id() === node.id()) {
        label = ({ branch_of: ['Has branch', 'دارای شعبه'], split_from: ['Split into', 'منشعب به'], successor: ['Predecessor to', 'پیشینِ'] })[edge.data('type')]?.[fa ? 1 : 0] || label;
      }
      if (!connected.has(other.id())) connected.set(other.id(), { node: other, descriptions: [] });
      connected.get(other.id()).descriptions.push([label, edge.data('role'), edge.data('note')].filter(Boolean).join(' · '));
    });
    el('connections-title').textContent = t(`Recorded connections · ${num(connected.size)}`, `پیوندهای ثبت‌شده · ${num(connected.size)}`);
    el('connections').replaceChildren(...[...connected.values()].sort((a, b) => a.node.data('label').localeCompare(b.node.data('label'), fa ? 'fa' : 'en'))
      .map((entry) => row(entry.node, [...new Set(entry.descriptions)].join(' / '))));
    el('connection-note').textContent = connected.size ? t('Choose an entry to follow the relationship.', 'برای دنبال کردن پیوند، مدخلی را انتخاب کنید.') : t('No specific relationship is recorded yet. The dashed connection places this entry in the revolution’s context.', 'هنوز پیوند مشخصی ثبت نشده است. خط‌چین این مدخل را در زمینهٔ انقلاب جای می‌دهد.');
    el('neighborhood').textContent = mode === 'local' ? t('Return to period', 'بازگشت به دوره') : t('Explore connections', 'کاوش پیوندها');
    caption();
    if (local) el('title').focus({ preventScroll: !mobile() });
  }
  function search() {
    const query = normalizeSearch(el('search').value);
    el('search-area').hidden = !query;
    el('results').replaceChildren();
    if (!query) return;
    const matches = records.filter((n) => enabled.has(n.data('kind')) && searchNames.get(n.id()).includes(query))
      .sort((a, b) => b.data('degree') - a.data('degree'));
    el('result-count').textContent = t(`${num(matches.length)} matches`, `${num(matches.length)} نتیجه`);
    matches.slice(0, 40).forEach((n) => el('results').append(row(n, periodName(n.data('primaryPeriod')))));
  }
  function zoom(factor) { cy.zoom({ level: cy.zoom() * factor, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }); }
  cy.on('tap', 'node', (event) => {
    const node = event.target;
    if (node.data('kind') === 'root') overview();
    else if (node.data('kind') === 'period') { limit = 12; periodView(node.data('period')); }
    else inspect(node);
  });
  cy.on('mouseover', 'node', (event) => {
    hovered = event.target;
    canvas.style.cursor = isRecord(hovered) ? 'grab' : 'pointer';
    const p = hovered.renderedPosition();
    el('tooltip').textContent = `${hovered.data('label')}${hovered.data('meta') ? ' · ' + hovered.data('meta') : ''}`;
    el('tooltip').style.left = `${Math.max(90, Math.min(cy.width() - 90, p.x))}px`;
    el('tooltip').style.top = `${Math.max(60, p.y - 25)}px`;
    el('tooltip').hidden = false;
    showEdges();
    scheduleTypography();
  });
  function clearHover() {
    hovered = null; canvas.style.cursor = ''; el('tooltip').hidden = true;
    showEdges();
  }
  cy.on('mouseout', 'node', clearHover);
  canvas.addEventListener('pointerleave', clearHover);
  cy.on('zoom pan position', scheduleTypography);
  cy.on('grab viewport', () => { el('tooltip').hidden = true; });
  checks.forEach((check) => check.addEventListener('change', () => {
    check.checked ? enabled.add(check.value) : enabled.delete(check.value);
    if (mode === 'overview') overview();
    else if (mode === 'period') periodView(currentEra, true);
    else if (selected && enabled.has(selected.data('kind'))) inspect(selected, true);
    else periodView(currentEra, true);
    search();
  }));
  root.querySelectorAll('[data-era]').forEach((button) => button.addEventListener('click', () => { limit = 12; periodView(button.dataset.era); }));
  el('search').addEventListener('input', search);
  el('search').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); el('results').querySelector('button')?.click(); }
    if (event.key === 'ArrowDown') { event.preventDefault(); el('results').querySelector('button')?.focus(); }
  });
  el('back').addEventListener('click', overview);
  el('reset').addEventListener('click', () => {
    Object.keys(NODE_TYPES).forEach((kind) => enabled.add(kind)); checks.forEach((check) => { check.checked = true; });
    el('search').value = ''; search(); overview();
  });
  el('fit').addEventListener('click', fitView);
  el('more').addEventListener('click', () => { limit += 12; periodView(currentEra, true); });
  el('clear').addEventListener('click', () => currentEra ? periodView(currentEra, true) : overview());
  el('neighborhood').addEventListener('click', () => {
    if (mode === 'local') periodView(currentEra);
    else if (selected) inspect(selected, true);
  });
  el('period-open').addEventListener('click', () => periodView(currentEra));
  root.querySelectorAll('[data-zoom]').forEach((button) => button.addEventListener('click', () => zoom(button.dataset.zoom === 'in' ? 1.25 : .8)));
  canvas.addEventListener('keydown', (event) => {
    const delta = { ArrowLeft: [60,0], ArrowRight: [-60,0], ArrowUp: [0,60], ArrowDown: [0,-60] }[event.key];
    if (delta) cy.panBy({ x: delta[0], y: delta[1] });
    else if (['+','='].includes(event.key)) zoom(1.25);
    else if (event.key === '-') zoom(.8);
    else if (event.key === '0') fitView();
    else if (event.key === 'Escape') currentEra ? periodView(currentEra) : overview();
    else return;
    event.preventDefault();
  });
  let width = canvas.clientWidth;
  const observer = new ResizeObserver(() => {
    cy.resize();
    if (Math.abs(width - canvas.clientWidth) > 50) { width = canvas.clientWidth; mode === 'overview' ? overview() : fitView(); }
    scheduleTypography();
  });
  observer.observe(canvas);
  overview();
  document.fonts.ready.then(scheduleTypography);
  window.addEventListener('pagehide', (event) => { if (!event.persisted) { observer.disconnect(); cy.destroy(); } });
}
