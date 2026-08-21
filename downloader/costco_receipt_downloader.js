/**
 * Costco Receipt Downloader (devtools console script)
 *
 * Usage:
 *   1. Log in to costco.com and navigate to Orders & Purchases -> In-Warehouse.
 *   2. Open devtools -> Console, paste this entire script, press Enter.
 *   3. Click "Load Existing Receipt File" (to merge/dedup against a previous
 *      export) or "Start Fresh (No File)".
 *   4. When fetching completes, choose Download JSON / Download CSV / Download Both.
 *
 * This is a personal-data archiving tool for the logged-in account owner.
 * It reads the auth tokens Costco's own web app already places in
 * localStorage and calls the same GraphQL endpoint the Orders & Purchases
 * page itself uses, with the same request shape (query, variables, headers)
 * that page's own JS sends — deviating from that shape (e.g. extra/renamed
 * GraphQL variables) gets rejected with a 403 by Costco's API gateway
 * before it ever reaches the resolver.
 *
 * Query/header shape adapted from TechStud/TCRDD
 * (https://github.com/TechStud/TCRDD), which reverse-engineered the real
 * request Costco's Orders & Purchases page sends.
 */
(function () {
  'use strict';

  const GRAPHQL_ENDPOINT = 'https://ecom-api.costco.com/ebusiness/order/v1/orders/graphql';
  // Costco's registered web-client identifier — a constant baked into their
  // own public JS bundle, not a per-user secret. Unrelated to the
  // per-account clientID/idToken pulled from localStorage below.
  const CLIENT_IDENTIFIER = '481b1aec-aa3b-454b-b81b-48187e28f205';

  // ---------------------------------------------------------------------
  // Auth
  // ---------------------------------------------------------------------

  function validateTokens() {
    const clientID = window.localStorage.getItem('clientID');
    const idToken = window.localStorage.getItem('idToken');
    if (!clientID || !idToken) {
      const msg =
        'Costco Receipt Downloader: missing clientID/idToken in localStorage. ' +
        'Make sure you are logged in to costco.com and on the Orders & Purchases page, then retry.';
      alert(msg);
      throw new Error(msg);
    }
    return { clientID, idToken };
  }

  // ---------------------------------------------------------------------
  // GraphQL — query/variables/headers must match what Costco's own page
  // sends. Do not add, rename, or wrap fields/variables here.
  // ---------------------------------------------------------------------

  const LIST_RECEIPTS_QUERY = `
    query receipts($startDate: String!, $endDate: String!) {
      receipts(startDate: $startDate, endDate: $endDate) {
        documentType
        receiptType
        membershipNumber
        transactionType
        transactionDateTime
        transactionDate
        warehouseShortName
        warehouseNumber
        warehouseName
        warehouseCity
        warehouseState
        warehouseAddress1
        warehouseAddress2
        warehousePostalCode
        transactionBarcode
        totalItemCount
        instantSavings
        subTotal
        taxes
        total
        registerNumber
        transactionNumber
        operatorNumber
        itemArray {
          itemNumber
          itemDescription01
          itemDescription02
          itemDepartmentNumber
          itemUnitPriceAmount
          unit
          amount
          taxFlag
          refundFlag
          voidFlag
          entryMethod
          fuelUnitQuantity
          fuelUomCode
          fuelGradeCode
        }
        couponArray {
          couponNumber
          associatedItemNumber
          amountCoupon
        }
        tenderArray {
          tenderTypeName
          amountTender
          walletType
          displayAccountNumber
          approvalNumber
          entryMethod
        }
      }
    }
  `;

  async function listReceipts(auth, startDate, endDate) {
    const headers = {
      'Content-Type': 'application/json',
      'Costco.Env': 'ecom',
      'Costco.Service': 'restOrders',
      'Costco-X-Wcs-Clientid': auth.clientID,
      'Client-Identifier': CLIENT_IDENTIFIER,
      'Costco-X-Authorization': `Bearer ${auth.idToken}`,
    };

    const body = JSON.stringify({
      query: LIST_RECEIPTS_QUERY.replace(/\s+/g, ' '),
      variables: { startDate, endDate },
    });

    const resp = await fetch(GRAPHQL_ENDPOINT, {
      method: 'POST',
      headers,
      body,
      // No `credentials: 'include'` — auth is via the Costco-X-Authorization
      // header above, not cookies, and ecom-api.costco.com's CORS policy
      // rejects credentialed cross-subdomain requests outright.
      credentials: 'omit',
    });

    if (!resp.ok) {
      const errorBody = await resp.json().catch(() => ({}));
      throw new Error(
        `Costco GraphQL request failed: ${resp.status} ${resp.statusText} — ${JSON.stringify(errorBody)}`
      );
    }

    const json = await resp.json();
    if (json.errors && json.errors.length) {
      throw new Error(`Costco GraphQL errors: ${JSON.stringify(json.errors)}`);
    }

    const receipts = json.data && json.data.receipts;
    if (!Array.isArray(receipts)) {
      throw new Error('Costco GraphQL response did not contain the expected receipts array.');
    }
    return receipts;
  }

  function maxDateRange() {
    // Costco max lookback: 3 years + 1 month back, floored to the 1st of
    // that month, through today. A single request covers the whole range.
    const now = new Date();
    const startDateObj = new Date(now);
    startDateObj.setFullYear(now.getFullYear() - 3);
    startDateObj.setMonth(startDateObj.getMonth() - 1);
    startDateObj.setDate(1);
    return {
      startDate: startDateObj.toISOString().slice(0, 10),
      endDate: now.toISOString().slice(0, 10),
    };
  }

  // ---------------------------------------------------------------------
  // Normalize / merge / dedup
  // ---------------------------------------------------------------------

  function receiptKey(r) {
    return `${r.membershipNumber}__${r.transactionBarcode}`;
  }

  function ensureArrays(r) {
    return {
      ...r,
      itemArray: Array.isArray(r.itemArray) ? r.itemArray : [],
      tenderArray: Array.isArray(r.tenderArray) ? r.tenderArray : [],
      couponArray: Array.isArray(r.couponArray) ? r.couponArray : [],
    };
  }

  function mergeReceipts(existing, incoming) {
    const byKey = new Map();
    for (const r of existing) byKey.set(receiptKey(r), ensureArrays(r));
    // Incoming (freshly fetched) wins on conflict, since it's the newer pull.
    for (const r of incoming) byKey.set(receiptKey(r), ensureArrays(r));
    return Array.from(byKey.values()).sort((a, b) =>
      (b.transactionDate || '').localeCompare(a.transactionDate || '')
    );
  }

  function perMemberStats(receipts) {
    const stats = new Map();
    for (const r of receipts) {
      const key = r.membershipNumber || 'unknown';
      if (!stats.has(key)) stats.set(key, { count: 0, total: 0 });
      const s = stats.get(key);
      s.count += 1;
      s.total += Number(r.total) || 0;
    }
    return stats;
  }

  function logStats(receipts) {
    const stats = perMemberStats(receipts);
    console.log(`Costco Receipt Downloader: ${receipts.length} total receipts.`);
    for (const [member, s] of stats.entries()) {
      console.log(`  Member ${member}: ${s.count} receipts, $${s.total.toFixed(2)} total`);
    }
  }

  // ---------------------------------------------------------------------
  // CSV export
  // ---------------------------------------------------------------------

  function csvEscape(value) {
    if (value === null || value === undefined) return '';
    const str = String(value);
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  }

  function csvRow(values) {
    return values.map(csvEscape).join(',') + '\r\n';
  }

  const RECEIPT_FIELDS = [
    'transactionDate',
    'warehouseName',
    'warehouseShortName',
    'warehouseCity',
    'warehouseState',
    'membershipNumber',
    'transactionBarcode',
    'total',
    'subTotal',
    'taxes',
    'instantSavings',
  ];

  const ITEM_FIELDS = [
    'itemNumber',
    'itemDescription01',
    'itemDescription02',
    'itemDepartmentNumber',
    'itemUnitPriceAmount',
    'unit',
    'amount',
    'taxFlag',
    'refundFlag',
    'voidFlag',
    'entryMethod',
  ];

  function toItemLevelCSV(receipts) {
    const header = [...RECEIPT_FIELDS, ...ITEM_FIELDS];
    let out = csvRow(header);
    for (const r of receipts) {
      const receiptValues = RECEIPT_FIELDS.map((f) => r[f]);
      const items = r.itemArray || [];
      for (const item of items) {
        const itemValues = ITEM_FIELDS.map((f) => item[f]);
        out += csvRow([...receiptValues, ...itemValues]);
      }
    }
    return out;
  }

  function toReceiptLevelCSV(receipts) {
    const header = [...RECEIPT_FIELDS, 'totalItemCount'];
    let out = csvRow(header);
    for (const r of receipts) {
      const values = RECEIPT_FIELDS.map((f) => r[f]);
      values.push(r.totalItemCount);
      out += csvRow(values);
    }
    return out;
  }

  // ---------------------------------------------------------------------
  // Save flow
  // ---------------------------------------------------------------------

  async function saveFile(contents, suggestedName, mimeType) {
    const blob = new Blob([contents], { type: mimeType });

    if (window.showSaveFilePicker) {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName,
          types: [
            {
              description: mimeType,
              accept: { [mimeType]: [`.${suggestedName.split('.').pop()}`] },
            },
          ],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        return;
      } catch (err) {
        if (err && err.name === 'AbortError') return; // user cancelled the picker
        console.warn('showSaveFilePicker failed, falling back to <a download>:', err);
      }
    }

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = suggestedName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function downloadJSON(receipts) {
    return saveFile(
      JSON.stringify({ exportedAt: new Date().toISOString(), receipts }, null, 2),
      'costco-receipts.json',
      'application/json'
    );
  }

  async function downloadCSV(receipts) {
    await saveFile(toItemLevelCSV(receipts), 'costco-receipts-items.csv', 'text/csv');
    await saveFile(toReceiptLevelCSV(receipts), 'costco-receipts.csv', 'text/csv');
  }

  // ---------------------------------------------------------------------
  // UI — step 1: load-existing-file / start-fresh prompt
  // ---------------------------------------------------------------------

  function getExistingReceipts() {
    return new Promise((resolve) => {
      let resolved = false;
      const container = document.createElement('div');
      container.id = 'costco-rd-prompt';
      Object.assign(container.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: '999999',
        display: 'flex',
        gap: '10px',
      });

      const loadBtn = document.createElement('button');
      loadBtn.textContent = 'Load Existing Receipt File';
      Object.assign(loadBtn.style, {
        padding: '10px 20px',
        backgroundColor: '#28a745',
        color: '#fff',
        border: 'none',
        borderRadius: '5px',
        cursor: 'pointer',
        fontSize: '14px',
      });

      const freshBtn = document.createElement('button');
      freshBtn.textContent = 'Start Fresh (No File)';
      Object.assign(freshBtn.style, {
        padding: '10px 20px',
        backgroundColor: '#6c757d',
        color: '#fff',
        border: 'none',
        borderRadius: '5px',
        cursor: 'pointer',
        fontSize: '14px',
      });

      const finish = (receipts) => {
        if (resolved) return;
        resolved = true;
        clearTimeout(timeoutId);
        container.remove();
        resolve(receipts);
      };

      freshBtn.addEventListener('click', () => {
        console.log('User selected to start fresh.');
        finish([]);
      });

      loadBtn.addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'application/json';
        input.onchange = (e) => {
          const file = e.target.files[0];
          if (!file) return;
          const reader = new FileReader();
          reader.onload = (event) => {
            try {
              const parsed = JSON.parse(event.target.result);
              const receipts = Array.isArray(parsed) ? parsed : parsed.receipts || [];
              console.log(`Loaded ${receipts.length} existing receipts from ${file.name}.`);
              finish(receipts);
            } catch (err) {
              console.error('Failed to parse existing receipts file:', err);
              finish([]);
            }
          };
          reader.readAsText(file);
        };
        input.click();
      });

      container.appendChild(loadBtn);
      container.appendChild(freshBtn);
      document.body.appendChild(container);

      const timeoutId = setTimeout(() => {
        console.log('No interaction within 30 seconds — starting fresh automatically.');
        finish([]);
      }, 30000);
    });
  }

  // ---------------------------------------------------------------------
  // UI — step 2: download-format picker, shown once fetch+merge is done
  // ---------------------------------------------------------------------

  function showDownloadPicker(receipts) {
    const existingPanel = document.getElementById('costco-rd-panel');
    if (existingPanel) existingPanel.remove();

    const panel = document.createElement('div');
    panel.id = 'costco-rd-panel';
    panel.style.cssText = [
      'position:fixed', 'bottom:16px', 'right:16px', 'z-index:999999',
      'background:#fff', 'color:#111', 'border:1px solid #ccc', 'border-radius:8px',
      'box-shadow:0 4px 16px rgba(0,0,0,0.25)', 'padding:14px', 'width:280px',
      'font:13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif',
    ].join(';');

    panel.innerHTML = `
      <div style="font-weight:600;margin-bottom:8px;">Costco Receipt Downloader</div>
      <div style="margin-bottom:10px;color:#555;">${receipts.length} receipts ready. Save as:</div>
      <button id="costco-rd-save-json" style="width:100%;padding:6px 0;margin-bottom:4px;cursor:pointer;">Download JSON</button>
      <button id="costco-rd-save-csv" style="width:100%;padding:6px 0;margin-bottom:4px;cursor:pointer;">Download CSV (both files)</button>
      <button id="costco-rd-save-both" style="width:100%;padding:6px 0;cursor:pointer;">Download Both</button>
    `;

    document.body.appendChild(panel);

    document.getElementById('costco-rd-save-json').addEventListener('click', () => downloadJSON(receipts));
    document.getElementById('costco-rd-save-csv').addEventListener('click', () => downloadCSV(receipts));
    document.getElementById('costco-rd-save-both').addEventListener('click', async () => {
      await downloadJSON(receipts);
      await downloadCSV(receipts);
    });
  }

  // ---------------------------------------------------------------------
  // Main
  // ---------------------------------------------------------------------

  async function main() {
    console.clear();
    console.log('--- Costco Receipt Downloader started ---');

    const auth = validateTokens();
    console.log('Authentication tokens found.');

    const existingReceipts = await getExistingReceipts();

    const { startDate, endDate } = maxDateRange();
    console.log(`Fetching receipts from ${startDate} to ${endDate}...`);

    let incoming;
    try {
      incoming = await listReceipts(auth, startDate, endDate);
    } catch (err) {
      console.error(err);
      alert(`Costco Receipt Downloader failed: ${err.message}. See console for details.`);
      return;
    }

    const merged = mergeReceipts(existingReceipts, incoming);
    logStats(merged);
    console.log(
      `Done. ${merged.length} receipts ready (${incoming.length} fetched, ${existingReceipts.length} from merge file).`
    );

    showDownloadPicker(merged);
  }

  main();
})();
