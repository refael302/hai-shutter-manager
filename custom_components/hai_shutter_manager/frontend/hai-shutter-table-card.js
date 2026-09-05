/**
 * HAI Shutter Manager dashboard card.
 *
 * One block per shutter, wrapping fields (no horizontal table). Updates in
 * place so Home Assistant state ticks do not reset scroll, close dropdowns,
 * or wipe values being edited.
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
  },
  he: {
    title: "מנהל תריסים",
    empty: "לא נמצאו תריסים מנוהלים. הוסף אותם בהגדרות האינטגרציה.",
    test: "מצב בדיקות — תריסים וירטואליים בלבד, לוג מפורט לטלגרם",
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
  },
};

const STYLES = `
  :host { display: block; }
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
  .list { display: flex; flex-direction: column; gap: 8px; }
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
  .reason { width: 100%; font-size: 12px; color: var(--secondary-text-color); }
  .fields {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 10px;
    margin-top: 10px;
    align-items: center;
  }
  .field { display: flex; align-items: center; gap: 6px; font-size: 13px; }
  .field label { color: var(--secondary-text-color); white-space: nowrap; }
  select.sel, input.num {
    color: var(--primary-text-color);
    background: var(--input-fill-color, var(--secondary-background-color, #eee));
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 4px;
    padding: 4px 6px;
    font: inherit;
  }
  input.num { width: 4.5em; text-align: center; }
  button.tog {
    cursor: pointer;
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 16px;
    padding: 4px 10px;
    font: inherit;
    font-size: 13px;
    color: var(--primary-text-color);
    background: var(--secondary-background-color, transparent);
    user-select: none;
  }
  button.tog.on {
    background: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
    border-color: transparent;
    font-weight: 600;
  }
`;

class HaiShutterTableCard extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._config = {};
    this._pending = new Map();
    this._built = false;
    this._rowEls = new Map();
  }

  setConfig(config) {
    this._config = config || {};
    if (this._built) {
      this._built = false;
      this._rowEls.clear();
      this._root().innerHTML = "";
      if (this._hass) this._sync();
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._sync();
  }

  getCardSize() {
    return Math.max(3, 2 + this._rows().length * 2);
  }

  static getStubConfig() {
    return {};
  }

  _t(key) {
    const lang = (this._hass?.language || "en").startsWith("he") ? "he" : "en";
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

  _ensureShell() {
    const root = this._root();
    if (this._built) return;
    root.innerHTML = `
      <ha-card>
        <div class="wrap">
          <div class="test-banner" hidden></div>
          <div class="empty" hidden></div>
          <div class="list"></div>
        </div>
      </ha-card>
      <style>${STYLES}</style>
    `;
    const card = root.querySelector("ha-card");
    card.header = this._config.title || this._t("title");
    this._banner = root.querySelector(".test-banner");
    this._empty = root.querySelector(".empty");
    this._list = root.querySelector(".list");
    this._card = card;
    this._built = true;
    this._rowEls.clear();
  }

  _rowTemplate(coverId) {
    const fields = FIELDS.map((field) => {
      if (field.type === "bool") {
        return `<button type="button" class="tog" data-key="${field.key}"></button>`;
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
      <div class="fields">${fields}</div>
    `;

    el.querySelectorAll("button.tog").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = btn.dataset.val !== "true";
        this._callSet(coverId, btn.dataset.key, next);
        this._paintBool(btn, next);
      });
    });
    el.querySelectorAll("input.num").forEach((input) => {
      input.addEventListener("change", () => {
        this._callSet(coverId, input.dataset.key, input.value);
      });
    });
    el.querySelectorAll("select.sel").forEach((select) => {
      select.addEventListener("change", () => {
        this._callSet(coverId, select.dataset.key, select.value);
      });
    });
    return el;
  }

  _paintBool(btn, on) {
    btn.dataset.val = on ? "true" : "false";
    btn.classList.toggle("on", on);
    btn.textContent = this._t(btn.dataset.key);
  }

  _paintRow(el, row) {
    el.querySelector(".name").textContent = row.name;

    const stateEl = el.querySelector(".state");
    const badge = !row.available ? "unavailable" : row.open ? "open" : "closed";
    stateEl.className = `state ${badge}`;
    stateEl.textContent = this._t(badge);

    const virtualEl = el.querySelector(".virtual");
    if (row.testMode && row.virtualState) {
      virtualEl.hidden = false;
      virtualEl.textContent = `${this._t("virtual")}: ${row.virtualState}`;
    } else {
      virtualEl.hidden = true;
    }

    const reasonEl = el.querySelector(".reason");
    if (row.reason) {
      reasonEl.hidden = false;
      reasonEl.textContent = row.reason;
    } else {
      reasonEl.hidden = true;
    }

    for (const field of FIELDS) {
      const incoming = this._displayValue(
        row.coverId,
        field.key,
        row.values[field.key]
      );
      if (field.type === "bool") {
        const btn = el.querySelector(`button.tog[data-key="${field.key}"]`);
        if (btn && !this._isBusy(btn)) this._paintBool(btn, this._asBool(incoming));
        continue;
      }
      if (field.type === "number") {
        const wrap = el.querySelector(`.field[data-key="${field.key}"]`);
        const input = wrap.querySelector("input");
        wrap.querySelector("label").textContent = this._t(field.key);
        if (!this._isBusy(input) && String(input.value) !== String(incoming)) {
          input.value = incoming;
        }
        continue;
      }
      const wrap = el.querySelector(`.field[data-key="${field.key}"]`);
      const select = wrap.querySelector("select");
      wrap.querySelector("label").textContent = this._t(field.key);
      if (!this._isBusy(select) && select.value !== String(incoming)) {
        select.value = incoming;
      }
    }
  }

  _sync() {
    if (!this._hass) return;
    this._ensureShell();
    this._card.header = this._config.title || this._t("title");

    const overview = this._overviewState();
    const testActive = Boolean(overview?.attributes?.test_mode);
    this._banner.hidden = !testActive;
    this._banner.textContent = this._t("test");

    const rows = this._rows();
    this._empty.hidden = rows.length > 0;
    this._empty.textContent = this._t("empty");

    const seen = new Set();
    for (const row of rows) {
      seen.add(row.coverId);
      let el = this._rowEls.get(row.coverId);
      if (!el) {
        el = this._rowTemplate(row.coverId);
        this._rowEls.set(row.coverId, el);
        this._list.appendChild(el);
      }
      this._paintRow(el, row);
    }
    for (const [coverId, el] of this._rowEls) {
      if (!seen.has(coverId)) {
        el.remove();
        this._rowEls.delete(coverId);
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
    description: "Per-shutter settings that wrap and stay editable while HA updates.",
  });
}

console.info("%c HAI-SHUTTER-TABLE-CARD %c loaded ", "background:#2e7d32;color:#fff", "");
