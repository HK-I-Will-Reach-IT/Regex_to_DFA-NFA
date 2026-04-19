// ui.js — DOM manipulation helpers

const UI = (() => {
    const $ = id => document.getElementById(id);

    function showLoader(visible) {
        $("loader").classList.toggle("hidden", !visible);
    }

    function showResult(data) {
        $("placeholder").classList.add("hidden");
        $("loader").classList.add("hidden");
        $("errorBox").classList.add("hidden");

        const resultEl = $("result");
        resultEl.classList.remove("hidden");

        $("metaRegex").textContent = `/${data.regex}/`;
        const badge = $("metaMode");
        badge.textContent = data.mode.toUpperCase();

        // ── Always replace diagram-wrap innerHTML (never touch #diagram directly)
        const diagramWrap = document.querySelector(".diagram-wrap");
        diagramWrap.innerHTML = Renderer.renderDiagram(data);

        $("tableContainer").innerHTML = Renderer.renderTable(data);
        $("rawJson").textContent = JSON.stringify(data, null, 2);
    }

    function showError(msg) {
        $("loader").classList.add("hidden");
        $("result").classList.add("hidden");
        $("placeholder").classList.add("hidden");
        const box = $("errorBox");
        box.textContent = "⚠ " + msg;
        box.classList.remove("hidden");
    }

    function renderHistory(items) {
        const list = $("historyList");
        list.innerHTML = "";
        if (!items.length) {
            list.innerHTML = `<li style="color:var(--muted);font-size:.8rem;font-family:var(--mono)">No history yet.</li>`;
            return;
        }
        [...items].reverse().forEach(item => {
            const li = document.createElement("li");
            li.className = "history-item";
            li.innerHTML = `
        <span class="hist-regex">${item.regex}<span class="hist-badge">${item.mode}</span></span>
        <span class="hist-meta">${item.states.length} states · ${item.timestamp.split("T")[0]}</span>
      `;
            // History click: show result AND sync the input field + mode toggle
            li.addEventListener("click", () => {
                document.getElementById("regexInput").value = item.regex;
                document.querySelectorAll(".toggle").forEach(b => {
                    b.classList.toggle("active", b.dataset.mode === item.mode);
                });
                showResult(item);
            });
            list.appendChild(li);
        });
    }

    return { showLoader, showResult, showError, renderHistory };
})();