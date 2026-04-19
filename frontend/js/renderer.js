// renderer.js — builds SVG diagram and transition table

const Renderer = (() => {

    /* ══════════════════════════════════════════════════════
       TRANSITION TABLE
    ══════════════════════════════════════════════════════ */
    function renderTable(data) {
        const { states, alphabet, transitions, start_state, accept_states } = data;
        const accepts = new Set(accept_states);

        const cols = [...alphabet];
        const hasEps = states.some(s => transitions[s] && transitions[s]["ε"]);
        if (hasEps) cols.push("ε");

        let html = "<table><thead><tr><th>State</th>";
        cols.forEach(c => (html += `<th>${c}</th>`));
        html += "</tr></thead><tbody>";

        states.forEach(s => {
            const isAccept = accepts.has(s);
            const isStart = s === start_state;
            let cls = "";
            if (isAccept) cls += " accept-row";
            if (isStart) cls += " start-row";
            html += `<tr class="${cls.trim()}">`;
            html += `<td>${isStart ? "→ " : ""}${s}${isAccept ? " *" : ""}</td>`;
            cols.forEach(sym => {
                const targets = (transitions[s] || {})[sym];
                html += `<td>${targets ? targets.join(", ") : "—"}</td>`;
            });
            html += "</tr>";
        });

        html += "</tbody></table>";
        return html;
    }

    /* ══════════════════════════════════════════════════════
       LAYOUT  (positions only — no canvas size yet)
    ══════════════════════════════════════════════════════ */
    const R = 26; // state circle radius

    function circularLayout(states) {
        const n = states.length;
        const radius = Math.max(100, n * 28);
        // Place the circle centred at origin; we'll translate via viewBox later
        const pos = {};
        states.forEach((s, i) => {
            const angle = (2 * Math.PI * i / n) - Math.PI / 2;
            pos[s] = { x: radius * Math.cos(angle), y: radius * Math.sin(angle) };
        });
        return pos;
    }

    function gridLayout(states) {
        const COLS = Math.min(states.length, 6);
        const COL_SEP = 130, ROW_SEP = 130;
        const pos = {};
        states.forEach((s, i) => {
            pos[s] = { x: (i % COLS) * COL_SEP, y: Math.floor(i / COLS) * ROW_SEP };
        });
        return pos;
    }

    function computePositions(states) {
        return states.length <= 8 ? circularLayout(states) : gridLayout(states);
    }

    /* ══════════════════════════════════════════════════════
       BOUNDING BOX  (accumulated while building SVG pieces)
    ══════════════════════════════════════════════════════ */
    function makeBBox() {
        let minX = Infinity, minY = Infinity;
        let maxX = -Infinity, maxY = -Infinity;
        function expand(x, y, pad = 0) {
            minX = Math.min(minX, x - pad);
            minY = Math.min(minY, y - pad);
            maxX = Math.max(maxX, x + pad);
            maxY = Math.max(maxY, y + pad);
        }
        return {
            expand,
            // Call after all elements are registered
            viewBox(margin = 18) {
                const x = minX - margin, y = minY - margin;
                const w = (maxX - minX) + margin * 2;
                const h = (maxY - minY) + margin * 2;
                return { x, y, w, h };
            },
        };
    }

    /* ══════════════════════════════════════════════════════
       SELF-LOOP: find the most open angular gap
    ══════════════════════════════════════════════════════ */
    function bestLoopDirection(state, fp, pos, edgeMap, start_state) {
        const angles = [];
        Object.values(edgeMap).forEach(({ from, to }) => {
            if (from === to) return;
            const neighbour = from === state ? to : to === state ? from : null;
            if (!neighbour) return;
            const np = pos[neighbour];
            angles.push(Math.atan2(np.y - fp.y, np.x - fp.x));
        });
        if (state === start_state) angles.push(Math.PI); // entry arrow from left
        if (angles.length === 0) return { nx: 0, ny: -1 };

        angles.sort((a, b) => a - b);
        let bestMid = -Math.PI / 2, bestGap = -Infinity;
        for (let i = 0; i < angles.length; i++) {
            const a1 = angles[i];
            const a2 = angles[(i + 1) % angles.length];
            const gap = a2 > a1 ? a2 - a1 : a2 - a1 + 2 * Math.PI;
            if (gap > bestGap) { bestGap = gap; bestMid = a1 + gap / 2; }
        }
        return { nx: Math.cos(bestMid), ny: Math.sin(bestMid) };
    }

    /* ══════════════════════════════════════════════════════
       CURVE HELPERS
    ══════════════════════════════════════════════════════ */
    function perp(ax, ay, bx, by) {
        const dx = bx - ax, dy = by - ay;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        return { x: -dy / len, y: dx / len };
    }

    function along(ax, ay, bx, by, d) {
        const dx = bx - ax, dy = by - ay;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        return { x: ax + dx / len * d, y: ay + dy / len * d };
    }

    function qbez(ax, ay, cx, cy, bx, by, t) {
        return {
            x: (1 - t) * (1 - t) * ax + 2 * (1 - t) * t * cx + t * t * bx,
            y: (1 - t) * (1 - t) * ay + 2 * (1 - t) * t * cy + t * t * by,
        };
    }

    /* ══════════════════════════════════════════════════════
       LABEL WITH BACKGROUND RECT
    ══════════════════════════════════════════════════════ */
    function labelRect(cx, cy, text, bb) {
        const pw = text.length * 6.8 + 8, ph = 16;
        bb.expand(cx, cy, Math.max(pw / 2, ph / 2));
        return `<rect x="${cx - pw / 2}" y="${cy - ph / 2}" width="${pw}" height="${ph}"
              rx="3" fill="#0a0c10" opacity=".88"/>
            <text x="${cx}" y="${cy}" fill="#00e5ff"
              font-family="'Space Mono',monospace" font-size="10"
              text-anchor="middle" dominant-baseline="central">${text}</text>`;
    }

    /* ══════════════════════════════════════════════════════
       SVG DIAGRAM
    ══════════════════════════════════════════════════════ */
    function renderDiagram(data) {
        const { states, transitions, start_state, accept_states } = data;
        const accepts = new Set(accept_states);
        const bb = makeBBox();

        /* ── Positions (centred around origin for now) ─── */
        const pos = computePositions(states);

        /* ── Collect & merge edges ───────────────────────── */
        const edgeMap = {};
        states.forEach(from => {
            Object.entries(transitions[from] || {}).forEach(([sym, targets]) => {
                targets.forEach(to => {
                    const key = `${from}→${to}`;
                    if (!edgeMap[key]) edgeMap[key] = { from, to, labels: [] };
                    edgeMap[key].labels.push(sym);
                });
            });
        });

        /* ─────────────────────────────────────────────────
           PASS 1: build all SVG element strings and
           simultaneously feed every coordinate into bb
        ───────────────────────────────────────────────── */
        let edgeSVG = "";
        let selfLoopSVG = "";
        let stateSVG = "";

        // Start-arrow — expands bb to the left of the start state
        const sp = pos[start_state];
        const arrStart = { x: sp.x - R - 38, y: sp.y };
        const arrEnd = { x: sp.x - R - 3, y: sp.y };
        bb.expand(arrStart.x, arrStart.y);
        bb.expand(arrEnd.x, arrEnd.y);
        const startArrowSVG =
            `<line x1="${arrStart.x}" y1="${arrStart.y}"
             x2="${arrEnd.x}"   y2="${arrEnd.y}"
             stroke="#ff3cac" stroke-width="2" marker-end="url(#arr-s)"/>`;

        // Regular edges
        Object.values(edgeMap).forEach(({ from, to, labels }) => {
            if (from === to) return;

            const label = labels.join(", ");
            const fp = pos[from], tp = pos[to];
            const bidir = !!edgeMap[`${to}→${from}`];
            const dx = tp.x - fp.x, dy = tp.y - fp.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;

            const bendMag = bidir
                ? Math.max(48, dist * 0.30)
                : Math.max(20, dist * 0.18);

            const mx = (fp.x + tp.x) / 2, my = (fp.y + tp.y) / 2;
            const pv = perp(fp.x, fp.y, tp.x, tp.y);
            const cpx = mx + pv.x * bendMag, cpy = my + pv.y * bendMag;

            const startPt = along(fp.x, fp.y, cpx, cpy, R + 1);
            const endPt = along(tp.x, tp.y, cpx, cpy, R + 5);

            // Expand bb with control point (a Bézier never exceeds its hull)
            bb.expand(cpx, cpy);
            bb.expand(startPt.x, startPt.y);
            bb.expand(endPt.x, endPt.y);

            edgeSVG +=
                `<path d="M${startPt.x},${startPt.y} Q${cpx},${cpy} ${endPt.x},${endPt.y}"
           fill="none" stroke="#6b7fa3" stroke-width="1.5" marker-end="url(#arr)"/>`;

            const mid = qbez(startPt.x, startPt.y, cpx, cpy, endPt.x, endPt.y, 0.5);
            edgeSVG += labelRect(mid.x + pv.x * 10, mid.y + pv.y * 10, label, bb);
        });

        // Self-loops
        Object.values(edgeMap).forEach(({ from, to, labels }) => {
            if (from !== to) return;

            const label = labels.join(", ");
            const fp = pos[from];
            const { nx, ny } = bestLoopDirection(from, fp, pos, edgeMap, start_state);

            const SPREAD = 0.44;
            const baseAngle = Math.atan2(ny, nx);
            const a1 = baseAngle - SPREAD, a2 = baseAngle + SPREAD;

            const x1 = fp.x + R * Math.cos(a1), y1 = fp.y + R * Math.sin(a1);
            const x2 = fp.x + R * Math.cos(a2), y2 = fp.y + R * Math.sin(a2);

            const LOOP_OUT = R * 2.6;
            const cx1 = fp.x + nx * LOOP_OUT + Math.cos(a1) * R * 0.5;
            const cy1 = fp.y + ny * LOOP_OUT + Math.sin(a1) * R * 0.5;
            const cx2 = fp.x + nx * LOOP_OUT + Math.cos(a2) * R * 0.5;
            const cy2 = fp.y + ny * LOOP_OUT + Math.sin(a2) * R * 0.5;

            // Tip of the loop (approx midpoint of the cubic) — register with bb
            const tipX = fp.x + nx * LOOP_OUT, tipY = fp.y + ny * LOOP_OUT;
            bb.expand(tipX, tipY, R * 0.5);

            selfLoopSVG +=
                `<path d="M${x1},${y1} C${cx1},${cy1} ${cx2},${cy2} ${x2},${y2}"
           fill="none" stroke="#6b7fa3" stroke-width="1.5" marker-end="url(#arr)"/>`;

            const LABEL_OUT = R * 3.1;
            selfLoopSVG += labelRect(
                fp.x + nx * LABEL_OUT,
                fp.y + ny * LABEL_OUT,
                label,
                bb
            );
        });

        // States — always expand bb
        states.forEach(s => {
            const { x, y } = pos[s];
            const isAccept = accepts.has(s);
            const isStart = s === start_state;
            bb.expand(x, y, R);

            const stroke = isAccept ? "#00ffa3" : isStart ? "#ff3cac" : "#00e5ff";
            const glow = isAccept
                ? "drop-shadow(0 0 7px rgba(0,255,163,.45))"
                : isStart
                    ? "drop-shadow(0 0 7px rgba(255,60,172,.35))"
                    : "drop-shadow(0 0 5px rgba(0,229,255,.2))";

            stateSVG +=
                `<circle cx="${x}" cy="${y}" r="${R}"
           fill="#111625" stroke="${stroke}" stroke-width="2"
           style="filter:${glow}"/>`;
            if (isAccept) {
                stateSVG +=
                    `<circle cx="${x}" cy="${y}" r="${R - 5}"
             fill="none" stroke="#00ffa3" stroke-width="1.1" opacity=".5"/>`;
            }
            stateSVG +=
                `<text x="${x}" y="${y}" fill="#e2e8f0"
           font-family="'Space Mono',monospace" font-size="11"
           text-anchor="middle" dominant-baseline="central">${s}</text>`;
        });

        /* ─────────────────────────────────────────────────
           PASS 2: derive viewBox from actual content bounds
        ───────────────────────────────────────────────── */
        const { x: vx, y: vy, w: vw, h: vh } = bb.viewBox(18);

        /* ── Assemble final SVG ──────────────────────────── */
        const svg =
            `<svg xmlns="http://www.w3.org/2000/svg"
            viewBox="${vx} ${vy} ${vw} ${vh}"
            style="display:block;width:100%;height:auto;">
        <defs>
          <marker id="arr"   markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M1,1 L7,4 L1,7 Z" fill="#6b7fa3"/>
          </marker>
          <marker id="arr-s" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M1,1 L7,4 L1,7 Z" fill="#ff3cac"/>
          </marker>
        </defs>
        ${startArrowSVG}
        ${edgeSVG}
        ${selfLoopSVG}
        ${stateSVG}
      </svg>`;

        return svg;
    }

    return { renderTable, renderDiagram };
})();