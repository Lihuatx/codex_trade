const $ = (id) => document.getElementById(id);

const STATUS_TEXT = {
  ok: '正常',
  approved: '通过',
  passed: '通过',
  failed: '失败',
  stale: '超时',
  no_log: '无日志',
  unknown: '未知',
  executed: '已执行',
  dry_run: '只读检查',
  no_actionable_intent: '无需调仓',
  cancelled: '已撤销',
  canceled: '已撤销',
  filled: '已成交',
  partially_filled: '部分成交',
  rejected: '已拒绝',
  expired: '已过期',
  live: '挂单中',
  submitted: '已提交',
  accepted: '已接受',
};

const SIDE_TEXT = {
  buy: '买入',
  sell: '卖出',
};

const ORDER_TYPE_TEXT = {
  post_only: 'Post-only',
  limit: '限价',
  market: '市价',
  ioc: 'IOC',
  fok: 'FOK',
};

async function loadStatus() {
  const response = await fetch('/api/status', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function setText(id, value) {
  $(id).textContent = display(value);
}

function display(value) {
  if (value == null || value === '') return '--';
  if (value === true) return '是';
  if (value === false) return '否';
  return String(value);
}

function translate(value) {
  if (value == null || value === '') return '--';
  if (value === true || value === false) return display(value);
  const key = String(value).toLowerCase();
  return STATUS_TEXT[key] || SIDE_TEXT[key] || ORDER_TYPE_TEXT[key] || String(value);
}

function formatTime(raw) {
  if (!raw) return '--';
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString('zh-CN', {
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function formatSeconds(value) {
  if (value == null) return '--';
  const seconds = Math.max(0, Math.round(Number(value)));
  if (seconds < 60) return `${seconds} 秒`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  if (minutes < 60) return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`;
  const hours = Math.floor(minutes / 60);
  const minuteRest = minutes % 60;
  return minuteRest ? `${hours} 小时 ${minuteRest} 分` : `${hours} 小时`;
}

function statusClass(value) {
  const key = String(value).toLowerCase();
  if (['cancelled', 'canceled'].includes(key)) {
    return 'cancel';
  }
  if (value === true || ['ok', 'passed', 'approved', 'executed', 'filled', 'dry_run'].includes(key)) {
    return 'ok';
  }
  if (['stale', 'no_log', 'no_actionable_intent', 'partially_filled', 'live', 'submitted', 'accepted'].includes(key)) {
    return 'warn';
  }
  if (value === false || ['failed', 'unknown', 'rejected', 'expired'].includes(key)) {
    return 'bad';
  }
  return '';
}

function sideNode(side) {
  const key = String(side || '').toLowerCase();
  const span = document.createElement('span');
  span.className = `side ${key}`;
  span.textContent = SIDE_TEXT[key] || display(side);
  return span;
}

function pill(value) {
  const span = document.createElement('span');
  span.className = `pill ${statusClass(value)}`;
  span.textContent = translate(value);
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
      dd.textContent = display(value);
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
      sideNode(order.side),
      ORDER_TYPE_TEXT[String(order.order_type).toLowerCase()] || order.order_type,
      order.price,
      order.size,
      pill(order.status),
      order.client_order_id,
    ];
    for (const value of cells) {
      const td = document.createElement('td');
      if (value instanceof Node) td.append(value);
      else td.textContent = display(value);
      tr.append(td);
    }
    body.append(tr);
  }
  if (!orders.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 8;
    td.textContent = '当前数据库还没有订单。';
    tr.append(td);
    body.append(tr);
  }
}

function renderEventList(node, rows, titleFn) {
  node.innerHTML = '';
  if (!rows.length) {
    const empty = document.createElement('div');
    empty.className = 'eventItem';
    empty.textContent = '暂无记录。';
    node.append(empty);
    return;
  }
  for (const row of rows) {
    const item = document.createElement('details');
    item.className = 'eventItem';
    const title = document.createElement('summary');
    title.className = 'eventTitle';
    const left = document.createElement('span');
    const dot = document.createElement('span');
    dot.className = `statusDot ${statusClass(eventStatus(row))}`;
    left.append(dot, document.createTextNode(titleFn(row)));
    const right = document.createElement('span');
    right.textContent = formatTime(row.created_at || row.started_at || row.finished_at);
    title.append(left, right);
    const pre = document.createElement('pre');
    pre.innerHTML = highlightJson(row);
    item.append(title, pre);
    node.append(item);
  }
}

function eventStatus(row) {
  if (row?.decision) return row.decision;
  if (row?.status) return row.status;
  if (row?.result?.ok === false) return 'failed';
  if (row?.result?.stage) return row.result.stage;
  if (row?.result?.ok === true) return 'ok';
  return 'unknown';
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function highlightJson(value) {
  const json = JSON.stringify(value, null, 2);
  return json.replace(
    /("(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(?:\s*:)?|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      const escaped = escapeHtml(match);
      if (match.endsWith(':')) return `<span class="json-key">${escaped}</span>`;
      if (match.startsWith('"')) return `<span class="json-string">${escaped}</span>`;
      if (match === 'true' || match === 'false') return `<span class="json-boolean">${escaped}</span>`;
      if (match === 'null') return `<span class="json-null">${escaped}</span>`;
      return `<span class="json-number">${escaped}</span>`;
    },
  );
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

function executionCount(state) {
  if (!state.executions_by_day) return 0;
  return Object.values(state.executions_by_day).reduce((sum, value) => sum + Number(value || 0), 0);
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
  setText('runnerHealth', translate(health.status));
  setText('cycles', state.cycles);
  setText('executions', executionCount(state));
  setText('errors', state.consecutive_errors);
  setText('ordersCount', counts.orders);
  setText('updatedAt', `刷新于 ${formatTime(data.generated_at)}`);
  setText('paths', `日志 ${data.paths?.log || '--'} | 数据库 ${data.paths?.db || '--'}`);
  setText('latestStage', translate(result.stage));
  $('latestStage').className = statusClass(result.stage);
  setText('orderSummary', `${counts.orders || 0} 笔订单 / ${counts.fills || 0} 笔成交`);
  setText('eventCount', `最近 ${(data.events || []).length} 条`);

  renderDetails($('latestDetails'), [
    ['健康年龄', formatSeconds(health.age_seconds)],
    ['当前周期', latest.cycle],
    ['周期开始', formatTime(latest.started_at)],
    ['周期结束', formatTime(latest.finished_at)],
    ['本轮真实下单', latest.executed_this_cycle],
    ['执行结果', pill(result.ok)],
    ['阶段', pill(result.stage)],
    ['本地状态', pill(result.localStatus)],
    ['交易所状态', pill(result.exchangeState)],
    ['Client Order ID', result.orderId],
    ['名义金额', result.notional],
  ]);

  renderDetails($('fileDetails'), [
    ['SQLite DB', data.paths?.db],
    ['JSONL 日志', data.paths?.log],
    ['Summary', data.paths?.summary],
    ['State', data.paths?.state],
    ['生成时间', formatTime(data.generated_at)],
  ]);

  renderOrders(db.orders || []);
  renderEventList($('riskList'), db.risk_events || [], (row) => {
    const decision = row.decision ? translate(row.decision) : '--';
    return `${row.inst_id || '--'} · ${decision}`;
  });
  renderEventList($('reconcileList'), db.reconciliation_runs || [], (row) => `对账 · ${translate(row.status)}`);
  renderEventList($('eventsList'), (data.events || []).slice().reverse(), (row) => {
    const item = eventResult(row);
    const okText = item.ok == null ? '--' : translate(item.ok);
    return `周期 ${row.cycle || '--'} · ${translate(item.stage || row.runner_event)} · ${okText}`;
  });
}

async function refresh() {
  try {
    updateDashboard(await loadStatus());
  } catch (error) {
    setText('runnerHealth', `加载失败：${error.message}`);
    $('runnerHealth').className = 'bad';
  }
}

$('refreshButton').addEventListener('click', refresh);
refresh();
setInterval(refresh, 10000);
