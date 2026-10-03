/**
 * app.js — Apex Banking DC App
 * Polls /api/cluster, /api/user, /api/transactions every 3 s.
 * No replication / DR logic here — that's handled by Nutanix NDK.
 */

const fmt = n => Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

let seenTxns = new Set();
let clusterName = '—';

// ── Toast ────────────────────────────────────────────────
function toast(title, msg, ok = true) {
  const el = document.getElementById('toast');
  document.getElementById('toast-title').textContent = title;
  document.getElementById('toast-message').textContent = msg;
  document.getElementById('toast-icon').innerHTML = ok
    ? '<i class="fa-solid fa-circle-check text-emerald-400"></i>'
    : '<i class="fa-solid fa-triangle-exclamation text-rose-400"></i>';
  el.className = el.className.replace(/bg-\S+|border-\S+/, '') +
    (ok ? ' bg-gray-900 border-emerald-500/40' : ' bg-gray-900 border-rose-500/40');
  el.style.opacity = '1';
  el.style.transform = 'translateY(0)';
  el.style.pointerEvents = 'auto';
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(-20px)';
    el.style.pointerEvents = 'none';
  }, 4000);
}

// ── Fetch cluster info ────────────────────────────────────
async function fetchCluster() {
  try {
    const r = await fetch('/api/cluster');
    if (!r.ok) return;
    const d = await r.json();
    clusterName = d.cluster_name;

    document.getElementById('cluster-name-text').textContent = d.cluster_name;
    document.getElementById('tt-pod').textContent     = d.pod_name  || '—';
    document.getElementById('tt-node').textContent    = d.node_name || '—';
    document.getElementById('tt-ns').textContent      = d.namespace || '—';
    document.getElementById('tt-region').textContent  = d.region    || '—';

    document.getElementById('info-cluster').textContent = d.cluster_name;
    document.getElementById('info-region').textContent  = d.region    || '—';
    document.getElementById('info-pod').textContent     = d.pod_name  || '—';
    document.getElementById('info-node').textContent    = d.node_name || '—';
    document.getElementById('info-ns').textContent      = d.namespace || '—';

    if (document.getElementById('modal-cluster'))
      document.getElementById('modal-cluster').textContent = d.cluster_name;
  } catch (e) { console.warn('cluster fetch:', e); }
}

// ── Fetch user ────────────────────────────────────────────
async function fetchUser() {
  try {
    const r = await fetch('/api/user');
    if (!r.ok) return;
    const u = await r.json();
    document.getElementById('user-name').textContent = u.full_name;
    document.getElementById('user-acc').textContent  = u.account_no;
    document.getElementById('balance').textContent   = fmt(u.balance);
  } catch (e) { console.warn('user fetch:', e); }
}

// ── Fetch transactions ────────────────────────────────────
async function fetchTransactions() {
  try {
    const r = await fetch('/api/transactions?limit=50');
    if (!r.ok) return;
    const txns = await r.json();

    document.getElementById('ledger-count').textContent = txns.length;
    document.getElementById('stat-total').textContent   = txns.length;
    document.getElementById('stat-credits').textContent = txns.filter(t => t.txn_type === 'CREDIT').length;
    document.getElementById('stat-debits').textContent  = txns.filter(t => t.txn_type === 'DEBIT').length;

    if (txns.length === 0) {
      document.getElementById('ledger-body').innerHTML =
        '<tr><td colspan="6" class="px-6 py-10 text-center text-gray-600">No transactions yet.</td></tr>';
      return;
    }

    let html = '';
    txns.forEach(t => {
      const isNew    = !seenTxns.has(t.txn_id);
      seenTxns.add(t.txn_id);
      const credit   = t.txn_type === 'CREDIT';
      const sign     = credit ? '+' : '−';
      const amtCls   = credit ? 'text-emerald-400' : 'text-rose-400';
      const time     = new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      html += `
        <tr class="${isNew ? 'row-new' : ''} hover:bg-gray-800/40 transition-colors">
          <td class="px-6 py-3">
            <div class="text-gray-200 font-semibold">${t.txn_id}</div>
            <div class="text-gray-500 text-[10px]">${time}</div>
          </td>
          <td class="px-4 py-3 max-w-xs">
            <div class="text-gray-200 truncate font-sans text-xs">${t.description}</div>
            <div class="text-gray-500 text-[10px] uppercase tracking-wider">${t.category}</div>
          </td>
          <td class="px-4 py-3">
            <span class="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-semibold
              bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 max-w-[160px] truncate"
              title="${t.cluster_name}">${t.cluster_name}</span>
          </td>
          <td class="px-4 py-3 text-right font-bold ${amtCls}">${sign}₹${fmt(t.amount)}</td>
          <td class="px-4 py-3 text-right text-gray-300">₹${fmt(t.balance_after)}</td>
          <td class="px-4 py-3 text-center">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold
              bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <i class="fa-solid fa-check mr-1"></i>COMMITTED
            </span>
          </td>
        </tr>`;
    });
    document.getElementById('ledger-body').innerHTML = html;
  } catch (e) { console.warn('txn fetch:', e); }
}

// ── Quick transaction ─────────────────────────────────────
async function quickTxn(type, cat, desc, amount) {
  try {
    const r = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'pankaj', txn_type: type, category: cat, description: desc, amount })
    });
    const d = await r.json();
    if (!r.ok) { toast('Transaction failed', d.error, false); return; }
    toast('Transaction committed', `₹${fmt(amount)} • ${d.cluster}`);
    fetchUser(); fetchTransactions();
  } catch { toast('Error', 'Could not reach the server', false); }
}

// ── Modal ─────────────────────────────────────────────────
function openTxnModal()  { document.getElementById('txn-modal').classList.remove('hidden'); }
function closeTxnModal() { document.getElementById('txn-modal').classList.add('hidden'); }

async function submitTxn(e) {
  e.preventDefault();
  const form = document.getElementById('txn-form');
  await quickTxn(
    form.elements['txn_type'].value,
    document.getElementById('f-cat').value,
    document.getElementById('f-desc').value,
    parseFloat(document.getElementById('f-amount').value)
  );
  form.reset();
  closeTxnModal();
}

// ── Reset ─────────────────────────────────────────────────
async function resetDemo() {
  if (!confirm("Reset Pankaj's account to the initial ₹5,00,000 state?")) return;
  await fetch('/api/reset', { method: 'POST' });
  seenTxns.clear();
  toast('Demo reset', 'Account returned to initial state.');
  fetchUser(); fetchTransactions();
}

// ── Refresh button ────────────────────────────────────────
function refresh() {
  const icon = document.getElementById('refresh-icon');
  icon.classList.add('fa-spin');
  Promise.all([fetchCluster(), fetchUser(), fetchTransactions()])
    .finally(() => setTimeout(() => icon.classList.remove('fa-spin'), 500));
}

// ── Boot + polling ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  refresh();
  setInterval(() => { fetchCluster(); fetchUser(); fetchTransactions(); }, 3000);
});
