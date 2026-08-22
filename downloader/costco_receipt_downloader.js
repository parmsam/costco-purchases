/**
 * Costco Receipt Downloader (devtools console script)
 *
 * Usage:
 *   1. Log in to costco.com and navigate to Orders & Purchases -> In-Warehouse.
 *   2. Open devtools -> Console, paste this entire script, press Enter.
 *   3. Optionally narrow the From/To date range (defaults to Costco's full
 *      ~3-year lookback - narrower is faster if you don't need it all),
 *      then click "Load Existing Receipt File" (to merge/dedup against a
 *      previous export) or "Start Fresh (No File)".
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
 * Covers in-warehouse merchandise AND gas station receipts (fetched via a
 * separate summary + per-barcode detail call — see graphqlRequest and
 * fetchGasStationReceipts below). Online orders (the "Online" tab) are a
 * different data shape entirely and are not fetched by this script.
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

  // receipts(startDate, endDate) only ever returns in-warehouse merchandise
  // receipts — gas station transactions are silently absent from it, not
  // just thinly detailed. Costco's own Orders & Purchases page gets gas
  // receipts via a second, per-receipt call: a receiptsWithCounts(startDate,
  // endDate, documentType:"all", documentSubType:"all") summary pass (which
  // also reports category counts) to find gas station barcodes, then one
  // receiptsWithCounts(barcode, documentType:"fuel") call per barcode for
  // the full itemized detail. See fetchGasStationReceipts() below.
  async function graphqlRequest(auth, query, variables) {
    const headers = {
      'Content-Type': 'application/json',
      'Costco.Env': 'ecom',
      'Costco.Service': 'restOrders',
      'Costco-X-Wcs-Clientid': auth.clientID,
      'Client-Identifier': CLIENT_IDENTIFIER,
      'Costco-X-Authorization': `Bearer ${auth.idToken}`,
    };

    const body = JSON.stringify({ query: query.replace(/\s+/g, ' '), variables });

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
    return json.data;
  }

  async function listReceipts(auth, startDate, endDate) {
    const data = await graphqlRequest(auth, LIST_RECEIPTS_QUERY, { startDate, endDate });
    const receipts = data && data.receipts;
    if (!Array.isArray(receipts)) {
      throw new Error('Costco GraphQL response did not contain the expected receipts array.');
    }
    return receipts;
  }

  const RECEIPT_SUMMARY_QUERY = `
    query receiptsWithCounts($startDate: String!, $endDate: String!, $documentType: String!, $documentSubType: String!) {
      receiptsWithCounts(startDate: $startDate, endDate: $endDate, documentType: $documentType, documentSubType: $documentSubType) {
        inWarehouse
        gasStation
        carWash
        gasAndCarWash
        receipts {
          receiptType
          documentType
          membershipNumber
          transactionBarcode
        }
      }
    }
  `;

  // Same field selection as LIST_RECEIPTS_QUERY above, so a gas station
  // receipt fetched this way slots into the merged receipts array with
  // exactly the same shape as a warehouse one — nothing downstream (merge,
  // CSV/JSON export, dashboard parser) needs to know it came from a
  // different query.
  const RECEIPT_DETAIL_QUERY = `
    query receiptsWithCounts($barcode: String!, $documentType: String!) {
      receiptsWithCounts(barcode: $barcode, documentType: $documentType) {
        receipts {
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
    }
  `;

  async function fetchReceiptDetail(auth, barcode, documentType) {
    const data = await graphqlRequest(auth, RECEIPT_DETAIL_QUERY, { barcode, documentType });
    const receipts = data && data.receiptsWithCounts && data.receiptsWithCounts.receipts;
    return Array.isArray(receipts) && receipts.length ? receipts[0] : null;
  }

  // Finds gas station receipts in the date range and fetches full itemized
  // detail for each. Best-effort: on failure this logs a warning and
  // returns [] rather than throwing, so a summary-query hiccup doesn't take
  // down the (already-working) warehouse-receipt fetch it runs alongside.
  async function fetchGasStationReceipts(auth, startDate, endDate) {
    let summary;
    try {
      const data = await graphqlRequest(auth, RECEIPT_SUMMARY_QUERY, {
        startDate,
        endDate,
        documentType: 'all',
        documentSubType: 'all',
      });
      summary = data && data.receiptsWithCounts;
    } catch (err) {
      console.warn('Gas station receipt lookup failed (continuing without them):', err);
      return [];
    }
    if (!summary) return [];

    console.log(
      `Receipt category counts — in-warehouse: ${summary.inWarehouse}, gas station: ${summary.gasStation}, ` +
        `car wash: ${summary.carWash}, gas+car wash: ${summary.gasAndCarWash}.`
    );

    const gasStubs = (summary.receipts || []).filter(
      (r) => r.receiptType === 'Gas Station' || r.documentType === 'FuelReceipts'
    );
    if (!gasStubs.length) return [];

    console.log(`Fetching detail for ${gasStubs.length} gas station receipt(s)...`);
    const detailed = [];
    for (const stub of gasStubs) {
      try {
        const receipt = await fetchReceiptDetail(auth, stub.transactionBarcode, 'fuel');
        if (receipt) detailed.push(receipt);
      } catch (err) {
        console.warn(`Failed to fetch gas station receipt ${stub.transactionBarcode}:`, err);
      }
    }
    return detailed;
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

  // Local time, not UTC - the timestamp is for the user glancing at their
  // downloads folder, not for machine parsing. Colon-free (HH-mm-ss) since
  // ':' isn't a legal filename character on Windows.
  function timestampSuffix() {
    const d = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return (
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
      `_${pad(d.getHours())}-${pad(d.getMinutes())}-${pad(d.getSeconds())}`
    );
  }

  function downloadJSON(receipts, suffix) {
    return saveFile(
      JSON.stringify({ exportedAt: new Date().toISOString(), receipts }, null, 2),
      `costco-receipts-${suffix}.json`,
      'application/json'
    );
  }

  async function downloadCSV(receipts, suffix) {
    await saveFile(toItemLevelCSV(receipts), `costco-receipts-items-${suffix}.csv`, 'text/csv');
    await saveFile(toReceiptLevelCSV(receipts), `costco-receipts-${suffix}.csv`, 'text/csv');
  }

  // ---------------------------------------------------------------------
  // UI — step 1: load-existing-file / start-fresh prompt
  // ---------------------------------------------------------------------

  // Resolves { existingReceipts, startDate, endDate }. Date inputs are
  // pre-filled with maxDateRange()'s full lookback window and left as-is
  // by default; narrowing them makes the fetch faster (fewer receipts, and
  // fewer per-barcode gas station detail calls - see
  // fetchGasStationReceipts) at the cost of only covering that window.
  function getDownloadOptions() {
    return new Promise((resolve) => {
      let resolved = false;
      const defaults = maxDateRange();

      const container = document.createElement('div');
      container.id = 'costco-rd-prompt';
      Object.assign(container.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        zIndex: '999999',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        background: '#fff',
        color: '#111',
        border: '1px solid #ccc',
        borderRadius: '8px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.25)',
        padding: '14px',
        width: '300px',
        font: '13px/1.4 -apple-system,Segoe UI,Roboto,sans-serif',
      });

      container.innerHTML = `
        <div style="font-weight:600;">Costco Receipt Downloader</div>
        <div style="display:flex;gap:8px;">
          <label style="flex:1;">From<br>
            <input id="costco-rd-start" type="date" value="${defaults.startDate}"
                   min="${defaults.startDate}" max="${defaults.endDate}" style="width:100%;">
          </label>
          <label style="flex:1;">To<br>
            <input id="costco-rd-end" type="date" value="${defaults.endDate}"
                   min="${defaults.startDate}" max="${defaults.endDate}" style="width:100%;">
          </label>
        </div>
        <div style="color:#666;font-size:11px;">Narrower range = faster download. Defaults to Costco's full ~3-year history.</div>
      `;

      const buttonRow = document.createElement('div');
      buttonRow.style.display = 'flex';
      buttonRow.style.gap = '10px';

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

      const finish = (existingReceipts) => {
        if (resolved) return;
        resolved = true;
        clearTimeout(timeoutId);

        const startInput = document.getElementById('costco-rd-start');
        const endInput = document.getElementById('costco-rd-end');
        let startDate = (startInput && startInput.value) || defaults.startDate;
        let endDate = (endInput && endInput.value) || defaults.endDate;
        if (startDate > endDate) [startDate, endDate] = [endDate, startDate]; // guard against a manually-typed inverted range

        container.remove();
        resolve({ existingReceipts, startDate, endDate });
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

      buttonRow.appendChild(loadBtn);
      buttonRow.appendChild(freshBtn);
      container.appendChild(buttonRow);
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

    // Computed once here (not inside downloadJSON/downloadCSV) so the JSON
    // and both CSV files from a single click - including "Download Both" -
    // always share one timestamp, even if a save-file-picker dialog delays
    // one of the saves into the next second.
    const suffix = timestampSuffix();

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

    document.getElementById('costco-rd-save-json').addEventListener('click', () => downloadJSON(receipts, suffix));
    document.getElementById('costco-rd-save-csv').addEventListener('click', () => downloadCSV(receipts, suffix));
    document.getElementById('costco-rd-save-both').addEventListener('click', async () => {
      await downloadJSON(receipts, suffix);
      await downloadCSV(receipts, suffix);
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

    const { existingReceipts, startDate, endDate } = await getDownloadOptions();
    console.log(`Fetching receipts from ${startDate} to ${endDate}...`);

    let incoming;
    try {
      incoming = await listReceipts(auth, startDate, endDate);
    } catch (err) {
      console.error(err);
      alert(`Costco Receipt Downloader failed: ${err.message}. See console for details.`);
      return;
    }

    console.log('Checking for gas station receipts (fetched separately - see comment on graphqlRequest)...');
    const gasStationReceipts = await fetchGasStationReceipts(auth, startDate, endDate);

    const merged = mergeReceipts(existingReceipts, [...incoming, ...gasStationReceipts]);
    logStats(merged);
    console.log(
      `Done. ${merged.length} receipts ready (${incoming.length} warehouse + ${gasStationReceipts.length} gas station fetched, ${existingReceipts.length} from merge file).`
    );

    showDownloadPicker(merged);
  }

  main();
})();
