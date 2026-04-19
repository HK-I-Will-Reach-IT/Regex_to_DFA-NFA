// main.js — entry point, wires up events

(async () => {
    /* ── State ─────────────────────────────────────────────── */
    let currentMode = "nfa";

    /* ── Elements ──────────────────────────────────────────── */
    const regexInput = document.getElementById("regexInput");
    const generateBtn = document.getElementById("generateBtn");
    const clearBtn = document.getElementById("clearBtn");
    const toggleBtns = document.querySelectorAll(".toggle");

    /* ── Mode toggle ───────────────────────────────────────── */
    toggleBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            toggleBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentMode = btn.dataset.mode;
        });
    });

    /* ── Generate ──────────────────────────────────────────── */
    async function generate() {
        const regex = regexInput.value.trim();
        if (!regex) {
            UI.showError("Please enter a regular expression.");
            return;
        }

        UI.showLoader(true);
        try {
            const data = await Api.generate(regex, currentMode);
            UI.showResult(data);
            loadHistory();
        } catch (err) {
            UI.showError(err.message);
        }
    }

    generateBtn.addEventListener("click", generate);
    regexInput.addEventListener("keydown", e => {
        if (e.key === "Enter") generate();
    });

    /* ── Clear history ─────────────────────────────────────── */
    clearBtn.addEventListener("click", async () => {
        try {
            await Api.clearHistory();
            UI.renderHistory([]);
        } catch (err) {
            console.error(err);
        }
    });

    /* ── Load history on boot ──────────────────────────────── */
    async function loadHistory() {
        try {
            const items = await Api.fetchHistory();
            UI.renderHistory(items);
        } catch (err) {
            console.error("History load failed:", err);
        }
    }

    loadHistory();
})();