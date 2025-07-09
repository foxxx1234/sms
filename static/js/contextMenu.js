// static/js/contextMenu.js

// Создаём контейнер для контекстного меню
const contextMenu = document.createElement("div");
contextMenu.id = "context-menu";
contextMenu.style.position = "absolute";
contextMenu.style.zIndex = "10000";
contextMenu.style.background = "#fff";
contextMenu.style.border = "1px solid #ccc";
contextMenu.style.borderRadius = "4px";
contextMenu.style.boxShadow = "0 2px 6px rgba(0,0,0,0.2)";
contextMenu.style.padding = "0.25rem 0";
contextMenu.style.display = "none";
document.body.appendChild(contextMenu);

// Опции меню по ТЗ
const menuItems = [
  { action: "connect", labelKey: "connect" },
  { action: "disconnect", labelKey: "disconnect" },
  { action: "ussd", labelKey: "ussd" },
  { action: "port_find", labelKey: "port_find" },
  { action: "port_sort", labelKey: "port_sort" },
  { action: "reload_ports", labelKey: "reload_ports" },
  { action: "settings", labelKey: "settings" },
];

// При инициализации вставляем пункты меню
function populateContextMenu(buttons, lang) {
  contextMenu.innerHTML = "";
  menuItems.forEach(item => {
    const btn = document.createElement("div");
    btn.className = "context-menu-item";
    btn.dataset.action = item.action;
    btn.textContent = buttons[item.labelKey][lang] || item.labelKey;
    btn.style.padding = "0.5rem 1rem";
    btn.style.cursor = "pointer";
    btn.addEventListener("mouseenter", () => {
      btn.style.background = "#f0f0f0";
    });
    btn.addEventListener("mouseleave", () => {
      btn.style.background = "";
    });
    contextMenu.appendChild(btn);
  });
}

// Показать меню для данного порта
function showContextMenu(x, y, port, buttons, lang) {
  populateContextMenu(buttons, lang);
  contextMenu.style.top = `${y}px`;
  contextMenu.style.left = `${x}px`;
  contextMenu.style.display = "block";

  // Навешиваем на каждый пункт действие
  contextMenu.querySelectorAll(".context-menu-item").forEach(item => {
    item.onclick = () => {
      const action = item.dataset.action;
      // Передаём порт в общую функцию action()
      if (action === "connect" || action === "disconnect") {
        fetch(`/api/${action}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ports: [port] })
        })
        .then(r => r.json())
        .then(data => {
          updateRow(data);
          if (action === "connect" && typeof window.startMonitoring === 'function') {
            window.startMonitoring([port]);
          }
          if (action === "disconnect" && typeof window.stopMonitoring === 'function') {
            window.stopMonitoring();
          }
        });
      } else if (action === "ussd") {
        openUSSDModal([port]);
      } else if (action === "port_find") {
        openPortFindModal([port]);
      } else if (action === "port_sort") {
        openPortSortModal();
      } else if (action === "reload_ports") {
        if (typeof window.loadPorts === 'function') window.loadPorts();
      } else if (action === "settings") {
        openSettingsModal();
      }
      hideContextMenu();
    };
  });
}

// Скрыть меню
function hideContextMenu() {
  contextMenu.style.display = "none";
}

// Обновить строку после действия (stub)
function updateRow(data) {
  if (data && data.results) {
    if (typeof window.updateRows === 'function') {
      window.updateRows(data.results);
    }
  }
  console.log("Context action result:", data);
}

// Обработчики открытия модальных окон (stub)
function openUSSDModal(ports) {
  // открывает окно ввода USSD для указанных портов
  alert(`USSD для портов: ${ports.join(", ")}`);
}
function openPortFindModal(ports) {
  alert(`Port Find для портов: ${ports.join(", ")}`);
}
function openPortSortModal() {
  alert("Port Sort");
}
function openSettingsModal() {
  alert("Settings");
}

// Скрываем меню по клику вне
document.addEventListener("click", e => {
  if (!e.target.closest("#context-menu")) {
    hideContextMenu();
  }
});

// Перехватываем контекстное меню на строках таблицы
document.addEventListener("contextmenu", e => {
  const row = e.target.closest("tr[data-port]");
  if (!row) return;
  e.preventDefault();
  const port = row.dataset.port;
  const buttons = window.buttons; // предполагаем, что buttons и lang доступны глобально
  const lang = window.lang || "en";
  showContextMenu(e.pageX, e.pageY, port, buttons, lang);
});
