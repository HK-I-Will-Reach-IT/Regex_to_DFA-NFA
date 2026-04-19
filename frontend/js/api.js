// api.js — all HTTP calls to the Flask backend

const API_BASE = "http://localhost:5000/api";

const Api = {
    async generate(regex, mode) {
        const res = await fetch(`${API_BASE}/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ regex, mode }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Server error");
        return data;
    },

    async fetchHistory() {
        const res = await fetch(`${API_BASE}/history`);
        if (!res.ok) throw new Error("Failed to load history");
        return res.json();
    },

    async clearHistory() {
        const res = await fetch(`${API_BASE}/history`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to clear history");
        return res.json();
    },
};