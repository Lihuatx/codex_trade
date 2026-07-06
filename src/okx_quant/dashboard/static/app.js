const $ = (id) => document.getElementById(id);

async function loadStatus() {
  const response = await fetch('/api/status', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`status ${response.status}`);
  }
  return response.json();
}

function setText(id, value) {
  $(id).textContent = value == null || value === '' ? '--' : String(value);
}

function formatTime(raw) {
  if (!raw) return '--';
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString();
}

function statusClass(value) {
  if (value === true || value === 'ok' || value === 'passed' || value === 'executed' || value === 'cancelled') {
    return 'ok';
  }
  if (value === 'stale' || value === 'dry_run' || value === 'no_log') return 'warn';
  if (value === false || value === 'failed' || value === 'unknown') return 'bad';
  return '';
}

function pill(value) {
  const span = document.createElement('span');
  span.className = `pill ${statusClass(value)}`;
  span.textContent = value == null ? '--' : String(value);
  return span;
}

function renderDetails(node, rows) {
  node.innerHTML = '';
  for (const [label, value] of rows) {
    const dt = document.createElement('dt');
    const dd = document.createElement('dd');
    dt.textContent = label;
    if (value instanceof Node) {
      dd.append(value);
    } else {
      dd.textContent = value == null || value === '' ? '--' : String(value);
    }
    node.append(dt, dd);
  }
}

function renderOrders(orders) {
  const body = $('ordersBody');
  body.innerHTML = '';
  for (const order of orders) {
    const tr = document.createElement('tr');
    const cells = [
      formatTime(order.updated_at),
      order.inst_id,
      order.side,
      order.order_type,
      order.price,
      order.size,
      pill(order.status),
      order.client_order_id,
    ];
    for (const value of cells) {
      const td = document.createElement('td');
      if (value instanceof Node) td.append(value);
      else td.textContent = value == null ? '--' : String(value);
      tr.append(td);
    }
    body.append(tr);
  }
  if (!orders.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 8;
    td.textContent = 'No orders in the selected DB.';
    tr.append(td);
    body.append(tr);
  }
}

function renderEventList(node, rows, titleFn) {
  node.innerHTML = '';
  if (!rows.length) {
    const empty = document.createElement('div');
    empty.className = 'eventItem';
    empty.textContent = 'No records.';
    node.append(empty);
    return;
  }
  for (const row of rows) {
    const item = document.createElement('div');
    item.className = 'eventItem';
    const title = document.createElement('div');
    title.className = 'eventTitle';
    const left = document.createElement('span');
    left.textContent = titleFn(row);
    const right = document.createElement('span');
    right.textContent = formatTime(row.created_at || row.started_at || row.finished_at);
    title.append(left, right);
    const pre = document.createElement('pre');
    pre.textContent = JSON.stringify(row, null, 2);
    item.append(title, pre);
    node.append(item);
  }
}

function eventResult(event) {
  const result = event?.result || {};
  return {
    ok: result.ok,
    stage: result.stage,
    localStatus: result.local_status,
    exchangeState: result.final_exchange_state,
    orderId: result.client_order_id,
    notional: result.rounded_notional,
  };
}

function updateDashboard(data) {
  const runner = data.runner || {};
  const health = runner.health || {};
  const latest = runner.latest_event || {};
  const state = runner.state || latest.state || {};
  const db = data.db || {};
  const counts = db.counts || {};
  const result = eventResult(latest);

  $('runnerHealth').className = statusClass(health.status);
  setText('runnerHealth', health.status);
  setText('cycles', state.cycles);
  const executions = state.executions_by_day
    ? Object.values(state.executions_by_day).reduce((a, b) => a + Number(b || 0), 0)
    : 0;
  setText('executions', executions);
  setText('errors', state.consecutive_errors);
  setText('ordersCount', counts.orders);
  setText('updatedAt', `Updated ${formatTime(data.generated_at)}`);
  setText('paths', `${data.paths?.log || '--'} | ${data.paths?.db || '--'}`);
  setText('latestStage', result.stage || '--');
  setText('orderSummary', `${counts.orders || 0} orders, ${counts.fills || 0} fills`);
  setText('eventCount', `${(data.events || []).length} JSONL events`);

  renderDetails($('latestDetails'), [
    ['Health age', health.age_seconds == null ? '--' : `${Math.round(health.age_seconds)}s`],
    ['Cycle', latest.cycle],
    ['Executed', latest.executed_this_cycle],
    ['OK', result.ok],
    ['Stage', result.stage],
    ['Local status', result.localStatus],
    ['Exchange state', result.exchangeState],
    ['Client order', result.orderId],
    ['Rounded notional', result.notional],
  ]);

  renderDetails($('fileDetails'), [
    ['DB', data.paths?.db],
    ['Log', data.paths?.log],
    ['Summary', data.paths?.summary],
    ['State', data.paths?.state],
    ['Generated', formatTime(data.generated_at)],
  ]);

  renderOrders(db.orders || []);
  renderEventList($('riskList'), db.risk_events || [], (row) => `${row.inst_id || '--'} ${row.decision || '--'}`);
  renderEventList($('reconcileList'), db.reconciliation_runs || [], (row) => `reconcile ${row.status || '--'}`);
  renderEventList($('eventsList'), (data.events || []).slice().reverse(), (row) => {
    const item = eventResult(row);
    return `cycle ${row.cycle || '--'} ${item.stage || row.runner_event || '--'}`;
  });
}

async function refresh() {
  try {
    updateDashboard(await loadStatus());
  } catch (error) {
    setText('runnerHealth', `load failed: ${error.message}`);
    $('runnerHealth').className = 'bad';
  }
}

$('refreshButton').addEventListener('click', refresh);
refresh();
setInterval(refresh, 10000);
