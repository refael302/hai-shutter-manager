/**
 * HAI Shutter Manager - table card.
 *
 * Renders one row per managed shutter with inline-editable settings. Editing
 * calls the `hai_shutter_manager.set_cover_option` service.
 */

const DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

const COLUMNS = [
  { key: "name", label: "Shutter", type: "name" },
  { key: "state", label: "State", type: "state" },
  { key: "virtual_state", label: "Virtual", type: "virtual" },
  { key: "direction", label: "Direction", type: "select", options: DIRECTIONS },
  { key: "close_evening", label: "Evening close", type: "bool" },
  { key: "open_morning", label: "Morning open", type: "bool" },
  { key: "close_rain", label: "Rain close", type: "bool" },
  { key: "desired_temp", label: "Desired temp", type: "number" },
  { key: "eave_length", label: "Eave (cm)", type: "number" },
  { key: "action_delay_hours", label: "Delay (h)", type: "number" },
  { key: "enabled", label: "Active", type: "bool" },
];

class HaiShutterTableCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 6;
  }

  _rows() {
    if (!this._hass) return [];
    const overview = this._overviewState();
    if (!overview) return [];
    const covers = overview.attributes.covers || {};
    return Object.entries(covers).map(([coverId, snapshot]) => {
      const cfg = snapshot.config || {};
      return {
        entityId: overview.entity_id,
        state: { state: snapshot.state === "open" ? "on" : "off" },
        attrs: {
          cover_id: coverId,
          available: snapshot.available,
          target: snapshot.target,
          reason: snapshot.reason,
          manual_until: snapshot.manual_until,
          last_action: snapshot.last_action,
          sun_hit: snapshot.sun_hit,
          sunlit_fraction: snapshot.sunlit_fraction,
          moves_today: snapshot.moves_today,
          test_mode: snapshot.test_mode,
          virtual_state: snapshot.virtual_state,
          ...cfg,
        },
      };
    }).sort((a, b) =>
      (a.attrs.cover_id || "").localeCompare(b.attrs.cover_id || "")
    );
  }

  _overviewState() {
    if (this._config.overview_entity) {
      return this._hass.states[this._config.overview_entity];
    }
    for (const entityId of Object.keys(this._hass.states)) {
      const state = this._hass.states[entityId];
      if (state.attributes && state.attributes.covers) {
        return state;
      }
    }
    return null;
  }

  _callSet(coverId, key, value) {
    this._hass.callService("hai_shutter_manager", "set_cover_option", {
      cover_id: coverId,
      key,
      value: String(value),
    });
  }

  _cellHtml(row, col) {
    const a = row.attrs;
    const coverId = a.cover_id;
    if (col.type === "name") {
      const name = this._friendlyName(coverId);
      return `<td class="name">${name}</td>`;
    }
    if (col.type === "state") {
      const open = row.state.state === "on";
      const txt = !a.target && !a.reason ? "" : a.reason || "";
      const badge = a.available === false ? "unavailable" : open ? "open" : "closed";
      return `<td class="state ${badge}" title="${this._esc(txt)}">${badge}</td>`;
    }
    if (col.type === "virtual") {
      if (!a.test_mode) return `<td class="virtual">-</td>`;
      return `<td class="virtual">${this._esc(a.virtual_state || "-")}</td>`;
    }
    if (col.type === "bool") {
      const on = a[col.key] === true || a[col.key] === "true";
      return `<td class="bool" data-cover="${coverId}" data-key="${col.key}" data-val="${on}">${
        on ? "V" : "X"
      }</td>`;
    }
    if (col.type === "number") {
      const val = a[col.key] != null ? a[col.key] : "";
      return `<td><input class="num" type="number" step="0.5" value="${val}" data-cover="${coverId}" data-key="${col.key}" /></td>`;
    }
    if (col.type === "select") {
      const cur = a[col.key] || "S";
      const opts = col.options
        .map(
          (o) =>
            `<option value="${o}" ${o === cur ? "selected" : ""}>${o}</option>`
        )
        .join("");
      return `<td><select class="sel" data-cover="${coverId}" data-key="${col.key}">${opts}</select></td>`;
    }
    return "<td></td>";
  }

  _friendlyName(coverId) {
    const st = this._hass.states[coverId];
    if (st && st.attributes && st.attributes.friendly_name) {
      return this._esc(st.attributes.friendly_name);
    }
    return this._esc(coverId);
  }

  _esc(s) {
    return String(s == null ? "" : s).replace(
      /[&<>"]/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])
    );
  }

  _render() {
    if (!this._hass) return;
    const rows = this._rows();

    const header = COLUMNS.map((c) => `<th>${c.label}</th>`).join("");
    const body = rows
      .map(
        (row) =>
          `<tr>${COLUMNS.map((c) => this._cellHtml(row, c)).join("")}</tr>`
      )
      .join("");

    const title = this._config.title || "Shutter Manager";
    const overview = this._overviewState();
    const testActive = overview?.attributes?.test_mode;
    const empty = rows.length
      ? ""
      : `<div class="empty">No managed shutters found. Add some via the integration options.</div>`;
    const testBanner = testActive
      ? `<div class="test-banner">TEST MODE — virtual shutters only, detailed logs to Telegram</div>`
      : "";

    this.innerHTML = `
      <ha-card header="${this._esc(title)}">
        <div class="wrap">
          ${testBanner}
          ${empty}
          <table>
            <thead><tr>${header}</tr></thead>
            <tbody>${body}</tbody>
          </table>
        </div>
      </ha-card>
      <style>
        .wrap { overflow-x: auto; padding: 8px 12px 16px; }
        table { border-collapse: collapse; width: 100%; font-size: 13px; }
        th, td { border-bottom: 1px solid var(--divider-color, #e0e0e0); padding: 6px 8px; text-align: center; white-space: nowrap; }
        th { color: var(--secondary-text-color); font-weight: 600; }
        td.name { text-align: start; font-weight: 600; }
        td.bool { cursor: pointer; font-weight: 700; user-select: none; }
        td.state.open { color: var(--success-color, #2e7d32); }
        td.state.closed { color: var(--secondary-text-color); }
        td.state.unavailable { color: var(--error-color, #c62828); }
        input.num { width: 64px; text-align: center; }
        .empty { padding: 12px; color: var(--secondary-text-color); }
        .test-banner {
          background: var(--warning-color, #f9a825);
          color: #000;
          padding: 8px 12px;
          border-radius: 4px;
          margin-bottom: 8px;
          font-weight: 600;
        }
        td.virtual { font-style: italic; color: var(--primary-color); }
      </style>
    `;

    this.querySelectorAll("td.bool").forEach((el) => {
      el.addEventListener("click", () => {
        const next = el.dataset.val !== "true";
        this._callSet(el.dataset.cover, el.dataset.key, next);
      });
    });
    this.querySelectorAll("input.num").forEach((el) => {
      el.addEventListener("change", () => {
        this._callSet(el.dataset.cover, el.dataset.key, el.value);
      });
    });
    this.querySelectorAll("select.sel").forEach((el) => {
      el.addEventListener("change", () => {
        this._callSet(el.dataset.cover, el.dataset.key, el.value);
      });
    });
  }
}

customElements.define("hai-shutter-table-card", HaiShutterTableCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "hai-shutter-table-card",
  name: "HAI Shutter Table Card",
  description: "Table view of all managed shutters and their settings.",
});

console.info("%c HAI-SHUTTER-TABLE-CARD %c loaded ", "background:#2e7d32;color:#fff", "");
