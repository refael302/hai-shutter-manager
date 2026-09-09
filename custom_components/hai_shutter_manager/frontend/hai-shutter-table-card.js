/**
 * HAI Shutter Manager dashboard card.
 *
 * Desktop (viewport ≥ 768px): one table for all shutters.
 * Phone (viewport under 768px): one wrapping block per shutter.
 * Updates in place so Home Assistant state ticks do not reset scroll,
 * close dropdowns, or wipe values being edited.
 */

const DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

const FIELDS = [
  { key: "direction", type: "select", options: DIRECTIONS },
  { key: "close_evening", type: "bool" },
  { key: "open_morning", type: "bool" },
  { key: "close_rain", type: "bool" },
  { key: "desired_temp", type: "number", step: "0.5" },
  { key: "eave_length", type: "number", step: "1" },
  { key: "action_delay_hours", type: "number", step: "0.5" },
  { key: "enabled", type: "bool" },
];

const I18N = {
  en: {
    title: "Shutter Manager",
    empty: "No managed shutters found. Add some via the integration options.",
    test: "TEST MODE — virtual shutters only, detailed logs to Telegram",
    shutter: "Shutter",
    state: "State",
    open: "open",
    closed: "closed",
    unavailable: "unavailable",
    virtual: "virtual",
    direction: "Direction",
    close_evening: "Evening close",
    open_morning: "Morning open",
    close_rain: "Rain close",
    desired_temp: "Temp",
    eave_length: "Eave cm",
    action_delay_hours: "Delay h",
    enabled: "Active",
    close_evening_short: "Evening",
    open_morning_short: "Morning",
    close_rain_short: "Rain",
    enabled_short: "Active",
  },
  he: {
    title: "מנהל תריסים",
    empty: "לא נמצאו תריסים מנוהלים. הוסף אותם בהגדרות האינטגרציה.",
    test: "מצב בדיקות — תריסים וירטואליים בלבד, לוג מפורט לטלגרם",
    shutter: "תריס",
    state: "מצב",
    open: "פתוח",
    closed: "סגור",
    unavailable: "לא זמין",
    virtual: "וירטואלי",
    direction: "כיוון",
    close_evening: "סגירת ערב",
    open_morning: "פתיחת בוקר",
    close_rain: "סגירת גשם",
    desired_temp: "טמפ'",
    eave_length: "גגון ס״מ",
    action_delay_hours: "השהיה ש׳",
    enabled: "פעיל",
    close_evening_short: "ערב",
    open_morning_short: "בוקר",
    close_rain_short: "גשם",
    enabled_short: "פעיל",
  },
};

const STYLES = `
  :host {
    display: block;
    width: 100%;
    max-width: none;
    container-type: inline-size;
    container-name: hai-shutter;
  }
  ha-card { width: 100%; box-sizing: border-box; }
  .wrap { padding: 4px 12px 16px; }
  .test-banner {
    background: var(--warning-color, #f9a825);
    color: #000;
    padding: 8px 12px;
    border-radius: 4px;
    margin-bottom: 10px;
    font-weight: 600;
  }
  .empty { padding: 12px; color: var(--secondary-text-color); }
  .list { display: none; flex-direction: column; gap: 8px; }
  .table-wrap { display: block; overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td {
    border-bottom: 1px solid var(--divider-color, #e0e0e0);
    padding: 6px 6px;
    text-align: center;
    vertical-align: middle;
    white-space: nowrap;
  }
  th { color: var(--secondary-text-color); font-weight: 600; }
  td.name-cell { text-align: start; min-width: 7em; white-space: normal; }
  .table-wrap.no-virtual .virtual-col { display: none; }
  .shutter {
    border: 1px solid var(--divider-color, #e0e0e0);
    border-radius: 8px;
    padding: 10px 12px;
    background: var(--card-background-color, transparent);
  }
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 6px 12px;
  }
  .name { font-weight: 700; }
  .status { display: flex; flex-wrap: wrap; gap: 8px; color: var(--secondary-text-color); font-size: 13px; }
  .state.open { color: var(--success-color, #2e7d32); font-weight: 600; }
  .state.closed { color: var(--secondary-text-color); }
  .state.unavailable { color: var(--error-color, #c62828); font-weight: 600; }
  .virtual { font-style: italic; color: var(--primary-color); }
  .reason { width: 100%; font-size: 12px; color: var(--secondary-text-color); font-weight: 400; }
  .fields {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 10px;
    margin-top: 10px;
    align-items: center;
  }
  .field { display: flex; align-items: center; gap: 6px; font-size: 13px; }
  td.field { display: table-cell; }
  .field label { color: var(--secondary-text-color); white-space: nowrap; }
  select.sel, input.num {
    color: var(--primary-text-color, #111);
    background: var(--input-fill-color, var(--secondary-background-color, #fff));
    border: 1px solid var(--divider-color, #888);
    border-radius: 4px;
    padding: 4px 6px;
    font: inherit;
  }
  input.num { width: 4.5em; text-align: center; }
  select.sel { min-width: 4.2em; }
  button.tog {
    cursor: pointer;
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 16px;
    min-width: 2.1em;
    padding: 4px 8px;
    font: inherit;
    font-size: 13px;
    font-weight: 700;
    line-height: 1.2;
    color: var(--primary-text-color);
    background: var(--secondary-background-color, transparent);
    user-select: none;
    white-space: nowrap;
  }
  button.tog.on {
    background: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
    border-color: transparent;
  }
  @media (max-width: 767px) {
    .list { display: flex; }
    .table-wrap { display: none; }
  }
`;

class HaiShutterTableCard extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._config = {};
    this._pending = new Map();
    this._built = false;
    this._cardEls = new Map();
    this._tableEls = new Map();
  }

  setConfig(config) {
    if (!config || typeof config !== "object") {
      this._config = {};
      return;
    }
    this._config = config;
    if (this._built) {
      this._built = false;
      this._cardEls.clear();
      this._tableEls.clear();
      this._root().innerHTML = "";
      if (this._hass) this._sync();
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._sync();
  }

  getCardSize() {
    const n = this._rows().length;
    return Math.max(3, 2 + n);
  }

  getGridOptions() {
    return HaiShutterTableCard.getGridOptions();
  }

  static getGridOptions() {
    return {
      columns: "full",
      min_columns: 6,
    };
  }

  static getStubConfig() {
    return {
      grid_options: { columns: "full" },
    };
  }

  _lang() {
    const forced = String(this._config.language || "").toLowerCase();
    if (forced.startsWith("en")) return "en";
    if (forced.startsWith("he")) return "he";
    const candidates = [
      this._hass?.locale?.language,
      this._hass?.language,
      this._hass?.selectedLanguage,
      document.documentElement.lang,
    ];
    for (const value of candidates) {
      if (!value) continue;
      if (String(value).toLowerCase().replace("_", "-").startsWith("he")) {
        return "he";
      }
    }
    return "he";
  }

  _t(key) {
    const lang = this._lang();
    return I18N[lang][key] || I18N.en[key] || key;
  }

  _root() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    return this.shadowRoot;
  }

  _overviewState() {
    if (!this._hass) return null;
    if (this._config.overview_entity) {
      return this._hass.states[this._config.overview_entity] || null;
    }
    for (const entityId of Object.keys(this._hass.states)) {
      const state = this._hass.states[entityId];
      if (state.attributes && state.attributes.covers) return state;
    }
    return null;
  }

  _rows() {
    const overview = this._overviewState();
    if (!overview) return [];
    const covers = overview.attributes.covers || {};
    return Object.entries(covers)
      .map(([coverId, snapshot]) => {
        const cfg = snapshot.config || {};
        return {
          coverId,
          name: this._friendlyName(coverId),
          available: snapshot.available !== false,
          open: snapshot.state === "open",
          reason: snapshot.reason || "",
          testMode: Boolean(snapshot.test_mode || overview.attributes.test_mode),
          virtualState: snapshot.virtual_state || "",
          values: {
            direction: cfg.direction || "S",
            close_evening: this._asBool(cfg.close_evening),
            open_morning: this._asBool(cfg.open_morning),
            close_rain: this._asBool(cfg.close_rain),
            desired_temp: cfg.desired_temp ?? "",
            eave_length: cfg.eave_length ?? "",
            action_delay_hours: cfg.action_delay_hours ?? "",
            enabled: this._asBool(cfg.enabled),
          },
        };
      })
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
  }

  _asBool(value) {
    return value === true || value === "true";
  }

  _friendlyName(coverId) {
    const st = this._hass?.states[coverId];
    if (st && st.attributes && st.attributes.friendly_name) {
      return st.attributes.friendly_name;
    }
    return coverId;
  }

  _displayValue(coverId, key, incoming) {
    const pending = this._pending.get(`${coverId}:${key}`);
    if (!pending) return incoming;
    if (Date.now() > pending.until) {
      this._pending.delete(`${coverId}:${key}`);
      return incoming;
    }
    if (String(incoming) === String(pending.value)) {
      this._pending.delete(`${coverId}:${key}`);
      return incoming;
    }
    return pending.value;
  }

  _remember(coverId, key, value) {
    this._pending.set(`${coverId}:${key}`, {
      value,
      until: Date.now() + 8000,
    });
  }

  _callSet(coverId, key, value) {
    this._remember(coverId, key, value);
    this._hass.callService("hai_shutter_manager", "set_cover_option", {
      cover_id: coverId,
      key,
      value: String(value),
    });
  }

  _isBusy(el) {
    const active = this._root().activeElement;
    return Boolean(active && (active === el || el.contains(active)));
  }

  _fieldControlsHtml() {
    return FIELDS.map((field) => {
      if (field.type === "bool") {
        return `<div class="field" data-key="${field.key}">
          <label></label>
          <button type="button" class="tog" data-key="${field.key}"></button>
        </div>`;
      }
      if (field.type === "number") {
        return `<div class="field" data-key="${field.key}">
          <label></label>
          <input class="num" type="number" step="${field.step}" data-key="${field.key}" />
        </div>`;
      }
      const opts = field.options
        .map((o) => `<option value="${o}">${o}</option>`)
        .join("");
      return `<div class="field" data-key="${field.key}">
        <label></label>
        <select class="sel" data-key="${field.key}">${opts}</select>
      </div>`;
    }).join("");
  }

  _bindControls(el, coverId) {
    el.querySelectorAll("button.tog").forEach((btn) => {
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        const next = btn.dataset.val !== "true";
        this._callSet(coverId, btn.dataset.key, next);
        this._paintBools(coverId, btn.dataset.key, next);
        btn.blur();
      });
    });
    el.querySelectorAll("input.num").forEach((input) => {
      const commit = () => {
        this._callSet(coverId, input.dataset.key, input.value);
        this._paintField(coverId, input.dataset.key, input.value);
      };
      input.addEventListener("input", commit);
      input.addEventListener("change", commit);
    });
    el.querySelectorAll("select.sel").forEach((select) => {
      select.addEventListener("change", () => {
        this._callSet(coverId, select.dataset.key, select.value);
        this._paintField(coverId, select.dataset.key, select.value);
      });
    });
  }

  _ensureShell() {
    const root = this._root();
    if (this._built) return;
    const fieldHeaders = FIELDS.map(
      (field) => `<th data-key="${field.key}"></th>`
    ).join("");
    root.innerHTML = `
      <ha-card>
        <div class="wrap">
          <div class="test-banner" hidden></div>
          <div class="empty" hidden></div>
          <div class="list"></div>
          <div class="table-wrap no-virtual">
            <table>
              <thead>
                <tr>
                  <th class="name-cell" data-key="shutter"></th>
                  <th data-key="state"></th>
                  <th class="virtual-col" data-key="virtual"></th>
                  ${fieldHeaders}
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      </ha-card>
      <style>${STYLES}</style>
    `;
    const card = root.querySelector("ha-card");
    card.header = this._config.title || this._t("title");
    this._banner = root.querySelector(".test-banner");
    this._empty = root.querySelector(".empty");
    this._list = root.querySelector(".list");
    this._tableWrap = root.querySelector(".table-wrap");
    this._thead = root.querySelector("thead");
    this._tbody = root.querySelector("tbody");
    this._card = card;
    this._built = true;
    this._cardEls.clear();
    this._tableEls.clear();
  }

  _cardTemplate(coverId) {
    const el = document.createElement("div");
    el.className = "shutter";
    el.dataset.cover = coverId;
    el.innerHTML = `
      <div class="head">
        <div class="name"></div>
        <div class="status">
          <span class="state"></span>
          <span class="virtual" hidden></span>
        </div>
        <div class="reason" hidden></div>
      </div>
      <div class="fields">${this._fieldControlsHtml()}</div>
    `;
    this._bindControls(el, coverId);
    return el;
  }

  _tableTemplate(coverId) {
    const tr = document.createElement("tr");
    tr.dataset.cover = coverId;
    const fieldCells = FIELDS.map((field) => {
      if (field.type === "bool") {
        return `<td><button type="button" class="tog" data-key="${field.key}"></button></td>`;
      }
      if (field.type === "number") {
        return `<td class="field" data-key="${field.key}">
          <input class="num" type="number" step="${field.step}" data-key="${field.key}" />
        </td>`;
      }
      const opts = field.options
        .map((o) => `<option value="${o}">${o}</option>`)
        .join("");
      return `<td class="field" data-key="${field.key}">
        <select class="sel" data-key="${field.key}">${opts}</select>
      </td>`;
    }).join("");
    tr.innerHTML = `
      <td class="name-cell">
        <div class="name"></div>
        <div class="reason" hidden></div>
      </td>
      <td><span class="state"></span></td>
      <td class="virtual-col"><span class="virtual"></span></td>
      ${fieldCells}
    `;
    this._bindControls(tr, coverId);
    return tr;
  }

  _paintBool(btn, on) {
    const full = this._t(btn.dataset.key);
    btn.dataset.val = on ? "true" : "false";
    btn.classList.toggle("on", on);
    btn.textContent = on ? "V" : "X";
    btn.title = full;
    btn.setAttribute("aria-label", full);
    const label = btn.parentElement?.querySelector("label");
    if (label) label.textContent = this._t(`${btn.dataset.key}_short`);
  }

  _eachView(coverId, fn) {
    const card = this._cardEls.get(coverId);
    const row = this._tableEls.get(coverId);
    if (card) fn(card);
    if (row) fn(row);
  }

  _paintBools(coverId, key, on) {
    this._eachView(coverId, (el) => {
      const btn = el.querySelector(`button.tog[data-key="${key}"]`);
      if (btn) this._paintBool(btn, on);
    });
  }

  _paintField(coverId, key, value) {
    this._eachView(coverId, (el) => {
      const field = FIELDS.find((item) => item.key === key);
      if (!field) return;
      if (field.type === "bool") {
        this._paintBools(coverId, key, this._asBool(value));
        return;
      }
      const wrap = el.querySelector(`.field[data-key="${key}"]`);
      if (!wrap) return;
      const input = wrap.querySelector("input, select");
      if (input && !this._isBusy(input) && String(input.value) !== String(value)) {
        input.value = value;
      }
    });
  }

  _paintStatus(el, row) {
    const nameEl = el.querySelector(".name");
    if (nameEl) nameEl.textContent = row.name;

    const stateEl = el.querySelector(".state");
    if (stateEl) {
      const badge = !row.available ? "unavailable" : row.open ? "open" : "closed";
      stateEl.className = `state ${badge}`;
      stateEl.textContent = this._t(badge);
    }

    const virtualEl = el.querySelector(".virtual");
    if (virtualEl) {
      if (row.testMode && row.virtualState) {
        virtualEl.hidden = false;
        virtualEl.textContent = `${this._t("virtual")}: ${row.virtualState}`;
      } else {
        virtualEl.hidden = true;
        virtualEl.textContent = "";
      }
    }

    const reasonEl = el.querySelector(".reason");
    if (reasonEl) {
      if (row.reason) {
        reasonEl.hidden = false;
        reasonEl.textContent = row.reason;
      } else {
        reasonEl.hidden = true;
      }
    }
  }

  _paintControls(el, row) {
    for (const field of FIELDS) {
      const incoming = this._displayValue(row.coverId, field.key, row.values[field.key]);
      if (field.type === "bool") {
        const btn = el.querySelector(`button.tog[data-key="${field.key}"]`);
        if (btn) this._paintBool(btn, this._asBool(incoming));
        continue;
      }
      const wrap = el.querySelector(`.field[data-key="${field.key}"]`);
      if (!wrap) continue;
      const label = wrap.querySelector("label");
      if (label) label.textContent = this._t(field.key);
      const input = wrap.querySelector("input, select");
      if (input && !this._isBusy(input) && String(input.value) !== String(incoming)) {
        input.value = incoming;
      }
    }
  }

  _paintHeaders() {
    this._thead.querySelectorAll("th[data-key]").forEach((th) => {
      th.textContent = this._t(th.dataset.key);
    });
  }

  _sync() {
    if (!this._hass) return;
    try {
      this._syncUnsafe();
    } catch (err) {
      console.error("hai-shutter-table-card failed to render", err);
      this._showError(err);
    }
  }

  _showError(err) {
    const root = this._root();
    root.innerHTML = `
      <ha-card header="HAI Shutter Manager">
        <div class="wrap">
          <div class="empty">${this._t("empty")}</div>
        </div>
      </ha-card>
      <style>${STYLES}</style>
    `;
    this._built = false;
    this._cardEls.clear();
    this._tableEls.clear();
    const empty = root.querySelector(".empty");
    if (empty) empty.hidden = false;
    void err;
  }

  _syncUnsafe() {
    this._ensureShell();
    this._root().querySelector(".wrap").setAttribute("dir", this._lang() === "he" ? "rtl" : "ltr");
    this._card.header = this._config.title || this._t("title");
    this._paintHeaders();

    const overview = this._overviewState();
    const testActive = Boolean(overview?.attributes?.test_mode);
    this._banner.hidden = !testActive;
    this._banner.textContent = this._t("test");
    this._tableWrap.classList.toggle("no-virtual", !testActive);

    const rows = this._rows();
    this._empty.hidden = rows.length > 0;
    this._empty.textContent = this._t("empty");
    this._list.hidden = rows.length === 0;
    this._tableWrap.hidden = rows.length === 0;

    const seen = new Set();
    for (const row of rows) {
      seen.add(row.coverId);
      let card = this._cardEls.get(row.coverId);
      if (!card) {
        card = this._cardTemplate(row.coverId);
        this._cardEls.set(row.coverId, card);
        this._list.appendChild(card);
      }
      let tr = this._tableEls.get(row.coverId);
      if (!tr) {
        tr = this._tableTemplate(row.coverId);
        this._tableEls.set(row.coverId, tr);
        this._tbody.appendChild(tr);
      }
      this._paintStatus(card, row);
      this._paintStatus(tr, row);
      this._paintControls(card, row);
      this._paintControls(tr, row);
    }
    for (const [coverId, el] of this._cardEls) {
      if (!seen.has(coverId)) {
        el.remove();
        this._cardEls.delete(coverId);
      }
    }
    for (const [coverId, el] of this._tableEls) {
      if (!seen.has(coverId)) {
        el.remove();
        this._tableEls.delete(coverId);
      }
    }
  }
}

if (!customElements.get("hai-shutter-table-card")) {
  customElements.define("hai-shutter-table-card", HaiShutterTableCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "hai-shutter-table-card")) {
  window.customCards.push({
    type: "hai-shutter-table-card",
    name: "HAI Shutter Table Card",
    description: "Table on wide dashboards, per-shutter cards on phones.",
  });
}

console.info("%c HAI-SHUTTER-TABLE-CARD %c loaded ", "background:#2e7d32;color:#fff", "");
