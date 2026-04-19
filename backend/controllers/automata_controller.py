from flask import Blueprint, request, jsonify
from services.automata_service import AutomataService

automata_bp = Blueprint("automata", __name__)
_service = AutomataService()


@automata_bp.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)
    regex = (data.get("regex") or "").strip()
    mode  = (data.get("mode") or "nfa").lower()

    if not regex:
        return jsonify({"error": "regex is required"}), 400
    if mode not in ("nfa", "dfa"):
        return jsonify({"error": "mode must be 'nfa' or 'dfa'"}), 400

    try:
        result = _service.generate(regex, mode)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        return jsonify({"error": f"Internal error: {exc}"}), 500


@automata_bp.route("/history", methods=["GET"])
def history():
    return jsonify(_service.history()), 200


@automata_bp.route("/history", methods=["DELETE"])
def clear_history():
    _service.clear_history()
    return jsonify({"message": "History cleared"}), 200