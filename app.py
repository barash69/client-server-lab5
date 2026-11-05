from flask import Flask, jsonify, request

app = Flask(__name__)

tasks = []

@app.route("/apihealth", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    return jsonify(tasks)

@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not isinstance(data.get("title"), str):
        return jsonify({"error": "Введите название задачи"}), 400

    title = data["title"].strip()

    if not title:
        return jsonify({"error": "Название не может быть пустым"}), 400

    task = {
        "id": len(tasks) + 1,
        "title": title
    }

    tasks.append(task)

    return jsonify(task), 201

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
