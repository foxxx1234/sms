// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
  //
  // Переводы и текущий язык из layout.html
  //
  const buttonsTrans = window.buttons;    // из translations.json → buttons
  const tabsTrans    = window.tabs;       // из translations.json → tabs
  const labelsTrans  = window.labels;     // из translations.json → table_headers
  const columnKeys   = (window.colKeys && window.colKeys.length) ? window.colKeys : Object.keys(labelsTrans);
  let currentLang    = window.lang || 'en';

  //
  // DOM-элементы
  //
  const selectAllCb     = document.getElementById('select-all');
  const table           = document.getElementById('modem-table');
  const thead           = table.querySelector('thead');
  const tbody           = table.querySelector('tbody');
  const logToggleBtn    = document.getElementById('toggle-log');
  const clearLogBtn     = document.getElementById('clear-log');
  const fileLogCb       = document.getElementById('file-log');
  const logEntries      = document.getElementById('log-entries');
  const langBtns        = document.querySelectorAll('.lang-btn');
  const menuBtns        = document.querySelectorAll('nav.main-menu .menu-btn');
  const tabBtns         = document.querySelectorAll('nav.tabs-menu .tab-btn');
  const contentSections = document.querySelectorAll('main#main-content section');

  //
  // Хранилище и состояние
  //
  let allPorts       = [];
  let displayedCount = 20;
  let sortKey        = null;
  let sortDir        = 1;  // 1 = возрастание, -1 = убывание
  let portInfo       = {};

  //
  // Добавить строку в лог
  //
  function log(msg) {
    const line = document.createElement('div');
    const ts   = new Date().toLocaleTimeString();
    line.textContent = `[${ts}] ${msg}`;
    logEntries.appendChild(line);
    logEntries.scrollTop = logEntries.scrollHeight;
    if (fileLogCb.checked) {
      // TODO: отправить на сервер для записи в файл (API)
    }
  }

  //
  // Отрисовать таблицу портов
  //
  function renderTable() {
    tbody.innerHTML = '';
    const subset = allPorts.length ? allPorts : Array.from({length: displayedCount}, () => null);
    subset.forEach(port => {
      const tr = document.createElement('tr');
      if (port) tr.dataset.port = port;
      let html = '';
      html += `<td><input type="checkbox" class="sel"${port ? '' : ' disabled'}></td>`;
      columnKeys.forEach(key => {
        let val = '—';
        if (port) {
          if (key === 'port') {
            val = port;
          } else if (portInfo[port] && portInfo[port][key] !== undefined) {
            val = portInfo[port][key];
          }
        }
        html += `<td class="${key}">${val}</td>`;
      });
      tr.innerHTML = html;
      tbody.appendChild(tr);
    });
    // Ограничиваем высоту таблицы 20 строками, если портов больше
    const rows = tbody.querySelectorAll('tr');
    const container = document.querySelector('section.modem-section');
    if (rows.length && container) {
      const rowHeight = rows[0].getBoundingClientRect().height;
      if (rows.length > displayedCount) {
        container.style.maxHeight = (rowHeight * displayedCount) + 'px';
        container.style.overflowY = 'auto';
      } else {
        container.style.maxHeight = '';
        container.style.overflowY = 'visible';
      }
    }
    log(`Rendered ${subset.length} ports`);
  }

  //
  // Обновить строки таблицы данными модемов
  //
  function updateRows(results) {
    let added = false;
    Object.keys(results).forEach(port => {
      let row = tbody.querySelector(`tr[data-port="${port}"]`);
      portInfo[port] = Object.assign({}, portInfo[port] || {}, results[port], { port });

      if (!row) {
        const tr = document.createElement('tr');
        tr.dataset.port = port;
        let html = '<td><input type="checkbox" class="sel"></td>';
        columnKeys.forEach(key => {
          const val = key === 'port' ? port : (results[port][key] !== undefined ? results[port][key] : '—');
          html += `<td class="${key}">${val}</td>`;
        });
        tr.innerHTML = html;
        tbody.appendChild(tr);
        row = tr;
        if (!allPorts.includes(port)) {
          allPorts.push(port);
          added = true;
        }
      } else {
        columnKeys.forEach(key => {
          const cell = row.querySelector(`td.${key}`);
          if (cell && results[port][key] !== undefined) {
            cell.textContent = results[port][key];
          }
        });
      }
    });
    if (added) {
      const rows = tbody.querySelectorAll('tr');
      const container = document.querySelector('section.modem-section');
      if (rows.length && container) {
        const rowHeight = rows[0].getBoundingClientRect().height;
        if (rows.length > displayedCount) {
          container.style.maxHeight = (rowHeight * displayedCount) + 'px';
          container.style.overflowY = 'auto';
        } else {
          container.style.maxHeight = '';
          container.style.overflowY = 'visible';
        }
      }
    }
    localStorage.setItem('portInfo', JSON.stringify(portInfo));
  }

  // делаем функцию глобальной, чтобы её вызывал contextMenu.js
  window.updateRows = updateRows;

  //
  // Загрузить порты из API
  //
  function loadPorts() {
    fetch('/api/scan_ports')
      .then(r => r.json())
      .then(data => {
        allPorts = data.ports || [];
        // добавляем сохранённые порты, если их нет в списке
        Object.keys(portInfo).forEach(p => {
          if (!allPorts.includes(p)) allPorts.push(p);
        });
        displayedCount = 20;
        renderTable();
        log(`Scanned ports: ${allPorts.length}`);
      })
      .catch(err => log(`Scan error: ${err}`));
  }

  //
  // Выполнить connect / disconnect
  //
  function doAction(action) {
    const selected = Array.from(tbody.querySelectorAll('.sel:checked'))
                          .map(cb => cb.closest('tr').dataset.port);
    const ports = selected.length ? selected : allPorts;

    if (action === 'connect') {

      fetch('/api/connect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify({ ports })
      })
      .then(async res => {
        if (res.ok && res.headers.get('Content-Type')?.startsWith('text/event-stream')) {
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            let idx;
            while ((idx = buffer.indexOf('\n\n')) !== -1) {
              const chunk = buffer.slice(0, idx).trim();
              buffer = buffer.slice(idx + 2);
              if (chunk.startsWith('data:')) {
                const data = chunk.slice(5).trim();
                try {
                  const info = JSON.parse(data);
                  updateRows({ [info.port]: info });
                  log(`connect: ${info.port}`);
                } catch (e) {
                  console.error(e);
                }
              }
            }
          }
          return null; // streamed
        }
        return res.json();
      })
      .then(res => {
        if (!res) return;
        if (res.results) {
          updateRows(res.results);
          log(`connect: ${Object.keys(res.results).join(', ')}`);
        } else if (res.ports) {
          log(`${action}: ${res.ports.join(', ')}`);
        } else {
          log(`${action}: ${JSON.stringify(res)}`);
        }
      })
      .catch(err => log(`connect error: ${err}`));

      return; // handled via streamed POST response only
    }

    fetch(`/api/${action}`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ ports })
    })
    .then(r => r.json())
    .then(res => {
      if (res.ports) {
        log(`${action}: ${res.ports.join(', ')}`);
      } else {
        log(`${action}: ${JSON.stringify(res)}`);
      }
    })
    .catch(err => log(`${action} error: ${err}`));
  }

  //
  // Переключение вкладок
  //
  function switchTab(tabKey) {
    tabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === tabKey));
    contentSections.forEach(sec => {
      sec.classList.toggle('hidden', sec.id !== `tab-${tabKey}`);
    });
  }

  //
  // Сортировка по порту (по алфавиту номера порта)
  //
  function sortBy(key) {
    sortDir = (sortKey === key) ? -sortDir : 1;
    sortKey = key;
    allPorts.sort((a, b) => {
      let A, B;
      if (key === 'port') {
        A = a.toLowerCase();
        B = b.toLowerCase();
      } else {
        A = (portInfo[a] && portInfo[a][key] !== undefined ? portInfo[a][key] : '').toString().toLowerCase();
        B = (portInfo[b] && portInfo[b][key] !== undefined ? portInfo[b][key] : '').toString().toLowerCase();
      }
      return A < B ? -sortDir : A > B ? sortDir : 0;
    });
    renderTable();
    log(`Sorted by ${key} (${sortDir>0?'asc':'desc'})`);
  }

  //
  // Обновить все тексты на странице по новому языку
  //
  function updateTexts() {
    // Главное меню
    menuBtns.forEach(b => {
      const act = b.dataset.action;
      b.textContent = buttonsTrans[act][currentLang];
    });
    // Вкладки
    tabBtns.forEach(b => {
      const tkey = b.dataset.tab;
      b.textContent = tabsTrans[tkey][currentLang];
    });
    // Заголовки таблицы
    thead.querySelectorAll('th.sortable').forEach(th => {
      const key = th.dataset.key;
      th.textContent = labelsTrans[key][currentLang];
    });
  }

  //
  // -------------- Устанавливаем обработчики --------------
  //

  // Select All
  selectAllCb.addEventListener('change', () => {
    const checked = selectAllCb.checked;
    tbody.querySelectorAll('.sel').forEach(cb => cb.checked = checked);
  });

  // Сортировка по клику на шапку
  thead.addEventListener('click', e => {
    const th = e.target.closest('th.sortable');
    if (!th) return;
    sortBy(th.dataset.key);
  });

  // Connect / Disconnect в меню
  document.querySelector('nav.main-menu .menu-btn[data-action="connect"]')
    .addEventListener('click', () => doAction('connect'));
  document.querySelector('nav.main-menu .menu-btn[data-action="disconnect"]')
    .addEventListener('click', () => doAction('disconnect'));

  // Заглушки для остальных действий
  ['ussd','port_find','port_sort','settings'].forEach(act => {
    document.querySelector(`nav.main-menu .menu-btn[data-action="${act}"]`)
      .addEventListener('click', () => alert(`${act} not implemented yet`));
  });

  // Лог: показать / скрыть
  logToggleBtn.addEventListener('click', () => {
    document.getElementById('log-panel').classList.toggle('hidden');
  });
  // Лог: очистить
  clearLogBtn.addEventListener('click', () => {
    logEntries.innerHTML = '';
  });

  // Вкладки
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Смена языка
  langBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const newLang = btn.dataset.lang;
      fetch('/set_language', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ lang: newLang })
      })
      .then(r => r.json())
      .then(json => {
        if (json.success) {
          currentLang = newLang;
          updateTexts();
        } else {
          alert('Не удалось сменить язык');
        }
      })
      .catch(err => {
        console.error(err);
        alert('Ошибка при смене языка');
      });
    });
  });

  //
  // ---------------- Инициализация ----------------
  //

  // Пометить заголовки с data-key как sortable
  thead.querySelectorAll('th').forEach(th => {
    if (th.dataset.key) th.classList.add('sortable');
  });

  // Загрузка сохранённой информации о портах
  try {
    const saved = localStorage.getItem('portInfo');
    if (saved) {
      portInfo = JSON.parse(saved);
      allPorts = Object.keys(portInfo);
    }
  } catch (e) {}

  renderTable();
  // Старт
  loadPorts();
  switchTab('ports');
});
