/**
 * CornerStone Agentic Score – Standalone onboarding flow.
 * Connect wallet, compliance & identity, allowlist, Borrower Signal, done.
 */

document.addEventListener('DOMContentLoaded', function () {
  // Console feedback to orient users
  console.log(
    '%cCornerStone Agentic Score',
    'font-weight:bold; font-size:12px;'
  );
  console.log(
    '1) Connect wallet → 2) Compliance & identity → 3) Register allowlist (multiple EVM/Aptos, optional testnet/mainnet) → copy env and MCP snippets.'
  );

  var API_BASE = window.ONBOARDING_API_BASE || '';
  var CREDITNEXUS_APP_URL = window.CREDITNEXUS_APP_URL || '';

  var currentStep = 1;
  var walletAddress = null;

  var PLAID_ENABLED = false;

  fetch((window.ONBOARDING_API_BASE || '') + '/config').then(function (r) { return r.json(); }).then(function (c) {
    if (c.api_base !== undefined) API_BASE = c.api_base;
    if (c.creditnexus_app_url) CREDITNEXUS_APP_URL = c.creditnexus_app_url;
    if (CREDITNEXUS_APP_URL) {
      var l1 = get('creditnexus-app-link');
      var l2 = get('creditnexus-app-link-2');
      if (l1) l1.href = CREDITNEXUS_APP_URL;
      if (l2) l2.href = CREDITNEXUS_APP_URL;
    }
    if (c.plaid_enabled) {
      PLAID_ENABLED = true;
      var plaidSection = get('plaid-section');
      if (plaidSection) plaidSection.style.display = 'block';
    }
  }).catch(function () {});

  function get(id) {
    return document.getElementById(id);
  }

  function showStep(step) {
    currentStep = step;
    var stepIds = ['step-wallet', 'step-banking', 'step-whitelist', 'step-openbank', 'step-done'];
    stepIds.forEach(function (id, i) {
      get(id).style.display = i + 1 === step ? 'block' : 'none';
    });
    document.querySelectorAll('#stepper .stepper-step').forEach(function (el, i) {
      el.classList.toggle('active', i + 1 === step);
      el.classList.toggle('done', i + 1 < step);
    });
  }

  function setWallet(addr) {
    walletAddress = addr;
    var wrap = get('wallet-connected');
    if (addr) {
      get('wallet-addr').textContent = addr;
      wrap.style.display = 'block';
      get('agent-address').value = addr;
      var first = firstEvmInput();
      if (first) first.value = addr;
    } else {
      wrap.style.display = 'none';
    }
  }

  function firstEvmInput() {
    var container = get('evm-wallets-container');
    return container ? container.querySelector('.evm-address') : null;
  }
  function syncAgentToWhitelist() {
    var agent = (get('agent-address').value || '').trim();
    var first = firstEvmInput();
    if (agent && first) first.value = agent;
  }

  // MetaMask connect
  get('btn-connect').addEventListener('click', function () {
    if (typeof window.ethereum === 'undefined') {
      alert('MetaMask is not installed. Please install the extension.');
      return;
    }
    window.ethereum
      .request({ method: 'eth_requestAccounts' })
      .then(function (accounts) {
        if (accounts && accounts[0]) {
          setWallet(accounts[0]);
        }
      })
      .catch(function (err) {
        console.error(err);
        alert('Failed to connect: ' + (err.message || 'Unknown error'));
      });
  });

  // Prefill first EVM row when user types in step 1 agent address
  get('agent-address').addEventListener('input', function () {
    var first = firstEvmInput();
    if (first) first.value = this.value.trim() || first.value;
  });

  get('btn-next-wallet').addEventListener('click', function () {
    syncAgentToWhitelist();
    showStep(2);
  });

  function setLinkStatus(text, isError) {
    var el = get('plaid-status');
    if (el) {
      el.textContent = text;
      el.className = 'plaid-status' + (isError ? ' error' : '');
    }
  }

  get('btn-plaid-connect').addEventListener('click', function () {
    if (!PLAID_ENABLED) return;
    setLinkStatus('Getting link…');
    fetch(API_BASE + '/plaid/link-token')
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d.error || d.detail || r.status); });
        return r.json();
      })
      .then(function (data) {
        var linkToken = data.link_token || data.linkToken;
        if (!linkToken) throw new Error('No link_token in response');
        setLinkStatus('Opening…');
        if (typeof Plaid !== 'undefined') {
          var link = Plaid.create({
            token: linkToken,
            onSuccess: function (publicToken) {
              setLinkStatus('Connecting…');
              var wallet = (get('agent-address').value || '').trim();
              var payload = { public_token: publicToken };
              if (wallet) payload.wallet = wallet;
              fetch(API_BASE + '/plaid/exchange', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
              })
                .then(function (res) {
                  if (!res.ok) return res.json().then(function (d) { throw new Error(d.error || d.detail || res.status); });
                  return res.json();
                })
                .then(function () {
                  setLinkStatus('Account linked.');
                })
                .catch(function (e) {
                  setLinkStatus(e.message || 'Exchange failed.', true);
                });
            },
            onExit: function () {
              setLinkStatus('');
            },
          });
          link.open();
        } else {
          setLinkStatus('Link script not loaded. Check console.', true);
        }
      })
      .catch(function (e) {
        setLinkStatus(e.message || 'Failed to get link token.', true);
      });
  });

  get('btn-next-banking').addEventListener('click', function () {
    syncAgentToWhitelist();
    var a = (get('agent-address').value || '').trim();
    var first = firstEvmInput();
    if (a && first) first.value = a;
    showStep(3);
  });

  // Valid EVM address: 0x + 40 hex or 40 hex. Aptos: 0x + 64 hex or 64 hex.
  function isValidEvm(addr) {
    var s = (addr || '').trim();
    return s && (s.match(/^0x[a-fA-F0-9]{40}$/) || s.match(/^[a-fA-F0-9]{40}$/));
  }
  function isValidAptos(addr) {
    var s = (addr || '').trim();
    return s && (s.match(/^0x[a-fA-F0-9]{64}$/) || s.match(/^[a-fA-F0-9]{64}$/));
  }

  // Add/remove wallet rows
  function addWalletRow(type) {
    var container = get(type === 'evm' ? 'evm-wallets-container' : 'aptos-wallets-container');
    var first = container.querySelector('.wallet-row');
    if (!first) return;
    var row = first.cloneNode(true);
    row.querySelector('.wallet-address').value = '';
    row.querySelector('.wallet-network').value = '';
    row.querySelector('.btn-remove-wallet').style.display = '';
    container.appendChild(row);
    row.querySelector('.btn-remove-wallet').addEventListener('click', function () { removeWalletRow(row, container); });
  }
  function removeWalletRow(row, container) {
    if (container.querySelectorAll('.wallet-row').length <= 1) return;
    row.remove();
  }
  get('btn-add-evm').addEventListener('click', function () { addWalletRow('evm'); });
  get('btn-add-aptos').addEventListener('click', function () { addWalletRow('aptos'); });
  document.querySelectorAll('#evm-wallets-container .btn-remove-wallet, #aptos-wallets-container .btn-remove-wallet').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var row = btn.closest('.wallet-row');
      var container = row && row.parentElement;
      if (row && container) removeWalletRow(row, container);
    });
  });

  // Register allowlist (EVM and/or Aptos agent addresses; multiple per type with optional network)
  get('btn-register').addEventListener('click', function () {
    var evmRows = (get('evm-wallets-container') || {}).querySelectorAll('.wallet-row') || [];
    var aptosRows = (get('aptos-wallets-container') || {}).querySelectorAll('.wallet-row') || [];
    var evmEntries = [];
    var aptosEntries = [];
    evmRows.forEach(function (row) {
      var addr = (row.querySelector('.evm-address').value || '').trim();
      var net = (row.querySelector('.wallet-network').value || '').trim() || null;
      if (addr) evmEntries.push({ address: addr, network: net });
    });
    aptosRows.forEach(function (row) {
      var addr = (row.querySelector('.aptos-address').value || '').trim();
      var net = (row.querySelector('.wallet-network').value || '').trim() || null;
      if (addr) aptosEntries.push({ address: addr, network: net });
    });
    var errEl = get('whitelist-error');
    errEl.style.display = 'none';

    if (!evmEntries.length && !aptosEntries.length) {
      errEl.textContent = 'Please enter at least one agent address: EVM (for open_bank_account) and/or Aptos (for run_prediction, run_backtest).';
      errEl.style.display = 'flex';
      return;
    }
    for (var i = 0; i < evmEntries.length; i++) {
      if (!isValidEvm(evmEntries[i].address)) {
        errEl.textContent = 'EVM address must be 0x followed by 40 hex characters.';
        errEl.style.display = 'flex';
        return;
      }
    }
    for (var j = 0; j < aptosEntries.length; j++) {
      if (!isValidAptos(aptosEntries[j].address)) {
        errEl.textContent = 'Aptos address must be 0x followed by 64 hex characters.';
        errEl.style.display = 'flex';
        return;
      }
    }

    var body = {};
    if (evmEntries.length === 1 && !evmEntries[0].network) body.agent_address = evmEntries[0].address;
    else if (evmEntries.length) body.agent_addresses = evmEntries;
    if (aptosEntries.length === 1 && !aptosEntries[0].network) body.aptos_agent_address = aptosEntries[0].address;
    else if (aptosEntries.length) body.aptos_agent_addresses = aptosEntries;
    var payToAddr = (get('pay-to-address') && get('pay-to-address').value ? get('pay-to-address').value : '').trim();
    if (payToAddr) body.pay_to_address = payToAddr;
    var fullName = (get('full-name').value || '').trim();
    var email = (get('email').value || '').trim();
    var address = (get('address').value || '').trim();
    if (fullName || email || address) {
      body.banking_application = { full_name: fullName || undefined, email: email || undefined, address: address || undefined };
    }

    fetch(API_BASE + '/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
      .then(function (res) {
        if (!res.ok) {
          return res.text().then(function (t) {
            throw new Error(t || 'Register failed: ' + res.status);
          });
        }
        return res.json();
      })
      .then(function (data) {
        get('env-snippet').textContent = data.env_snippet || '';
        get('mcp-snippet').textContent = JSON.stringify(data.mcp_snippet || {}, null, 2);
        get('snippets-area').style.display = 'block';
        var envExportEl = get('env-export-cmd');
        if (envExportEl) envExportEl.textContent = 'eval $(curl -s ' + (window.location.origin || '') + '/env-export)';
        console.log(
          'Whitelist registered. Paste env snippet into demo_mcp/server/.env and MCP snippet into .cursor/mcp.json. Terminal: eval $(curl -s ' + (window.location.origin || '') + '/env-export) or set ONBOARDING_HYDRO_ENV_FILE and source that file.'
        );
      })
      .catch(function (e) {
        errEl.textContent = e.message || 'Registration failed.';
        errEl.style.display = 'flex';
      });
  });

  get('copy-env').addEventListener('click', function () {
    var pre = get('env-snippet');
    var btn = get('copy-env');
    if (pre && pre.textContent) {
      navigator.clipboard.writeText(pre.textContent).then(function () {
        btn.title = 'Copied!';
        setTimeout(function () { btn.title = 'Copy'; }, 1500);
      });
    }
  });

  get('copy-mcp').addEventListener('click', function () {
    var pre = get('mcp-snippet');
    var btn = get('copy-mcp');
    if (pre && pre.textContent) {
      navigator.clipboard.writeText(pre.textContent).then(function () {
        btn.title = 'Copied!';
        setTimeout(function () { btn.title = 'Copy'; }, 1500);
      });
    }
  });

  get('btn-next-whitelist').addEventListener('click', function () {
    showStep(4);
  });

  get('btn-next-openbank').addEventListener('click', function () {
    showStep(5);
  });

  showStep(1);
});
