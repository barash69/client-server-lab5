import sqlite3
from flask import Flask, jsonify, request

app = Flask(__name__)
DB = "/home/vlad/lab5/tasks.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.create_function(
        "UNICODE_CASEFOLD",
        1,
        lambda s: s.casefold() if s is not None else "",
        deterministic=True
    )
    return conn


def error(message, status=400):
    return jsonify({"error": message}), status


def task_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "completed": bool(row["completed"]),
        "created_at": row["created_at"]
    }


@app.route("/apihealth", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/tasks/stats", methods=["GET"])
def task_stats():
    with get_db() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(completed), 0) AS completed
            FROM tasks
        """).fetchone()

    total = row["total"]
    completed = row["completed"]
    active = total - completed

    completion_percent = (
        (completed * 100 + total // 2) // total
        if total > 0 else 0
    )

    return jsonify({
        "total": total,
        "completed": completed,
        "active": active,
        "completion_percent": completion_percent
    })

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "all")
    page_value = request.args.get("page", "1")
    limit_value = request.args.get("limit", "10")

    if status not in ("all", "active", "completed"):
        return error("Некорректный статус задачи")

    try:
        page = int(page_value)
        limit = int(limit_value)
    except ValueError:
        return error("page и limit должны быть целыми числами")

    if page < 1:
        return error("page должен быть не меньше 1")

    if not 1 <= limit <= 50:
        return error("limit должен быть от 1 до 50")

    conditions = []
    params = []

    if q:
        conditions.append(
            "instr(UNICODE_CASEFOLD(title), ?) > 0"
        )
        params.append(q.casefold())

    if status == "active":
        conditions.append("completed = ?")
        params.append(0)
    elif status == "completed":
        conditions.append("completed = ?")
        params.append(1)

    where_sql = (
        " WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM tasks" + where_sql,
            params
        ).fetchone()[0]

        offset = (page - 1) * limit

        rows = conn.execute(
            "SELECT * FROM tasks" + where_sql +
            " ORDER BY created_at DESC, id DESC"
            " LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()

    total_pages = (total + limit - 1) // limit

    return jsonify({
        "items": [task_to_dict(row) for row in rows],
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages
    })


@app.route("/api/tasks", methods=["POST"])
def add_task():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error("Некорректные данные")

    title = data.get("title")

    if not isinstance(title, str):
        return error("Название задачи должно быть строкой")

    title = title.strip()

    if not 1 <= len(title) <= 200:
        return error("Название должно содержать от 1 до 200 символов")

    completed = data.get("completed", False)

    if not isinstance(completed, bool):
        return error("Поле completed должно быть логическим")

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (title, completed) VALUES (?, ?)",
            (title, int(completed))
        )
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (cursor.lastrowid,)
        ).fetchone()

    return jsonify(task_to_dict(row)), 201


@app.route("/api/tasks/<int:task_id>", methods=["PATCH"])
def update_task(task_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error("Некорректные данные")

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()

        if row is None:
            return error("Задача не найдена", 404)

        title = row["title"]
        completed = bool(row["completed"])

        if "title" in data:
            if not isinstance(data["title"], str):
                return error("Название задачи должно быть строкой")

            title = data["title"].strip()

            if not 1 <= len(title) <= 200:
                return error(
                    "Название должно содержать от 1 до 200 символов"
                )

        if "completed" in data:
            if not isinstance(data["completed"], bool):
                return error(
                    "Поле completed должно быть логическим"
                )
            completed = data["completed"]

        conn.execute(
            "UPDATE tasks SET title = ?, completed = ? WHERE id = ?",
            (title, int(completed), task_id)
        )

        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,)
        ).fetchone()

    return jsonify(task_to_dict(updated))


@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )

        if cursor.rowcount == 0:
            return error("Задача не найдена", 404)

    return jsonify({"message": "Задача удалена"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
