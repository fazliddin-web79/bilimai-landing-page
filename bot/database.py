import asyncio
import csv
import io
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REGISTRATION_COLUMNS = [
    "id",
    "participant_code",
    "telegram_id",
    "telegram_username",
    "parent_full_name",
    "phone",
    "student_full_name",
    "grade",
    "current_school",
    "neighborhood",
    "olympiad_location",
    "source",
    "attended",
    "created_at",
    "updated_at",
]

ANSWER_SUBMISSION_COLUMNS = [
    "id",
    "participant_code",
    "student_full_name",
    "grade",
    "olympiad_location",
    "answers_text",
    "correct_count",
    "total_questions",
    "checked_at",
    "created_at",
    "updated_at",
]


@dataclass(frozen=True)
class RegistrationInput:
    telegram_id: int
    telegram_username: Optional[str]
    parent_full_name: str
    phone: str
    student_full_name: str
    grade: str
    current_school: str
    neighborhood: str
    olympiad_location: str
    source: str


class DuplicateTelegramError(ValueError):
    pass


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path))
        connection.row_factory = sqlite3.Row
        return connection

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        parent = self.path.parent
        if str(parent):
            parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS registrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participant_code TEXT UNIQUE,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    telegram_username TEXT,
                    parent_full_name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    student_full_name TEXT NOT NULL,
                    grade TEXT NOT NULL CHECK (grade IN ('2-sinf', '3-sinf', '4-sinf')),
                    current_school TEXT NOT NULL,
                    neighborhood TEXT NOT NULL,
                    olympiad_location TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'unknown',
                    attended INTEGER NOT NULL DEFAULT 0 CHECK (attended IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_registrations_phone
                    ON registrations(phone);
                CREATE INDEX IF NOT EXISTS idx_registrations_student_name
                    ON registrations(student_full_name);
                CREATE INDEX IF NOT EXISTS idx_registrations_parent_name
                    ON registrations(parent_full_name);

                CREATE TABLE IF NOT EXISTS answer_keys (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    answers_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS answer_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registration_id INTEGER NOT NULL,
                    telegram_id INTEGER NOT NULL UNIQUE,
                    participant_code TEXT NOT NULL,
                    answers_text TEXT NOT NULL,
                    correct_count INTEGER,
                    total_questions INTEGER NOT NULL DEFAULT 30,
                    checked_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (registration_id)
                        REFERENCES registrations(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_answer_submissions_code
                    ON answer_submissions(participant_code);
                """
            )

    async def create_registration(self, data: RegistrationInput) -> Dict[str, Any]:
        return await asyncio.to_thread(self._create_registration_sync, data)

    def _create_registration_sync(self, data: RegistrationInput) -> Dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO registrations (
                        telegram_id, telegram_username, parent_full_name, phone,
                        student_full_name, grade, current_school, neighborhood,
                        olympiad_location, source, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data.telegram_id,
                        data.telegram_username,
                        data.parent_full_name,
                        data.phone,
                        data.student_full_name,
                        data.grade,
                        data.current_school,
                        data.neighborhood,
                        data.olympiad_location,
                        data.source,
                        now,
                        now,
                    ),
                )
                row_id = int(cursor.lastrowid)
                participant_code = f"AS-{row_id:04d}"
                connection.execute(
                    "UPDATE registrations SET participant_code = ? WHERE id = ?",
                    (participant_code, row_id),
                )
                row = connection.execute(
                    "SELECT * FROM registrations WHERE id = ?", (row_id,)
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            if "telegram_id" in str(exc):
                raise DuplicateTelegramError(
                    "Bu Telegram ID orqali avval ro'yxatdan o'tilgan."
                ) from exc
            raise
        return dict(row)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._get_one, "telegram_id", telegram_id)

    async def get_by_code(self, participant_code: str) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(
            self._get_one, "participant_code", participant_code.upper()
        )

    def _get_one(self, column: str, value: Any) -> Optional[Dict[str, Any]]:
        if column not in {"telegram_id", "participant_code"}:
            raise ValueError("Noto'g'ri qidiruv ustuni.")
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT * FROM registrations WHERE {column} = ?", (value,)
            ).fetchone()
        return dict(row) if row else None

    async def phone_count(self, phone: str, exclude_telegram_id: Optional[int] = None) -> int:
        return await asyncio.to_thread(self._phone_count_sync, phone, exclude_telegram_id)

    def _phone_count_sync(self, phone: str, exclude_telegram_id: Optional[int]) -> int:
        query = "SELECT COUNT(*) AS count FROM registrations WHERE phone = ?"
        params: List[Any] = [phone]
        if exclude_telegram_id is not None:
            query += " AND telegram_id != ?"
            params.append(exclude_telegram_id)
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return int(row["count"])

    async def search(self, query: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._search_sync, query)

    def _search_sync(self, query: str) -> List[Dict[str, Any]]:
        value = f"%{query.strip()}%"
        code = query.strip().upper()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM registrations
                WHERE participant_code = ?
                   OR phone LIKE ?
                   OR parent_full_name LIKE ?
                   OR student_full_name LIKE ?
                ORDER BY id DESC
                LIMIT 20
                """,
                (code, value, value, value),
            ).fetchall()
        return [dict(row) for row in rows]

    async def all_registrations(self) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._all_registrations_sync)

    def _all_registrations_sync(self) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM registrations ORDER BY id ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    async def recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._recent_sync, limit)

    def _recent_sync(self, limit: int) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM registrations ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 50)),),
            ).fetchall()
        return [dict(row) for row in rows]

    async def today(self) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._today_sync)

    def _today_sync(self) -> List[Dict[str, Any]]:
        today = datetime.now().date().isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM registrations
                WHERE substr(created_at, 1, 10) = ?
                ORDER BY id DESC
                """,
                (today,),
            ).fetchall()
        return [dict(row) for row in rows]

    async def delete_by_code(self, participant_code: str) -> bool:
        return await asyncio.to_thread(self._delete_by_code_sync, participant_code)

    def _delete_by_code_sync(self, participant_code: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM registrations WHERE participant_code = ?",
                (participant_code.upper(),),
            )
        return cursor.rowcount > 0

    async def mark_attended(self, participant_code: str) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._mark_attended_sync, participant_code)

    def _mark_attended_sync(self, participant_code: str) -> Optional[Dict[str, Any]]:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE registrations
                SET attended = 1, updated_at = ?
                WHERE participant_code = ?
                """,
                (now, participant_code.upper()),
            )
            row = connection.execute(
                "SELECT * FROM registrations WHERE participant_code = ?",
                (participant_code.upper(),),
            ).fetchone()
        return dict(row) if row else None

    async def update_field(
        self, participant_code: str, field: str, value: str
    ) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(
            self._update_field_sync, participant_code, field, value
        )

    def _update_field_sync(
        self, participant_code: str, field: str, value: str
    ) -> Optional[Dict[str, Any]]:
        editable = {
            "parent_full_name",
            "phone",
            "student_full_name",
            "grade",
            "current_school",
            "neighborhood",
            "olympiad_location",
            "source",
        }
        if field not in editable:
            raise ValueError("Bu maydonni tahrirlab bo'lmaydi.")
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            connection.execute(
                f"UPDATE registrations SET {field} = ?, updated_at = ? WHERE participant_code = ?",
                (value, now, participant_code.upper()),
            )
            row = connection.execute(
                "SELECT * FROM registrations WHERE participant_code = ?",
                (participant_code.upper(),),
            ).fetchone()
        return dict(row) if row else None

    async def stats(self) -> Dict[str, Any]:
        return await asyncio.to_thread(self._stats_sync)

    def _stats_sync(self) -> Dict[str, Any]:
        today = datetime.now().date().isoformat()
        with self._connect() as connection:
            total = self._count(connection, "SELECT COUNT(*) FROM registrations")
            today_count = self._count(
                connection,
                "SELECT COUNT(*) FROM registrations WHERE substr(created_at, 1, 10) = ?",
                (today,),
            )
            attended = self._count(
                connection, "SELECT COUNT(*) FROM registrations WHERE attended = 1"
            )
            by_grade = self._group_counts(connection, "grade")
            by_location = self._group_counts(connection, "olympiad_location")
            by_source = self._group_counts(connection, "source")
        return {
            "total": total,
            "today": today_count,
            "attended": attended,
            "not_attended": total - attended,
            "by_grade": by_grade,
            "by_location": by_location,
            "by_source": by_source,
        }

    def _count(
        self, connection: sqlite3.Connection, query: str, params: Iterable[Any] = ()
    ) -> int:
        return int(connection.execute(query, tuple(params)).fetchone()[0])

    def _group_counts(
        self, connection: sqlite3.Connection, column: str
    ) -> Dict[str, int]:
        if column not in {"grade", "olympiad_location", "source"}:
            raise ValueError("Noto'g'ri statistika ustuni.")
        rows = connection.execute(
            f"SELECT {column} AS label, COUNT(*) AS count FROM registrations GROUP BY {column} ORDER BY count DESC"
        ).fetchall()
        return {row["label"]: int(row["count"]) for row in rows}

    async def export_csv(self) -> bytes:
        rows = await self.all_registrations()
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.DictWriter(output, fieldnames=REGISTRATION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in REGISTRATION_COLUMNS})
        return output.getvalue().encode("utf-8")

    async def set_answer_key(self, answers_text: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._set_answer_key_sync, answers_text)

    def _set_answer_key_sync(self, answers_text: str) -> Dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO answer_keys (id, answers_text, created_at, updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    answers_text = excluded.answers_text,
                    updated_at = excluded.updated_at
                """,
                (answers_text, now, now),
            )
            row = connection.execute(
                "SELECT * FROM answer_keys WHERE id = 1"
            ).fetchone()
        return dict(row)

    async def get_answer_key(self) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._get_answer_key_sync)

    def _get_answer_key_sync(self) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM answer_keys WHERE id = 1"
            ).fetchone()
        return dict(row) if row else None

    async def save_answer_submission(
        self,
        registration: Dict[str, Any],
        answers_text: str,
        correct_count: Optional[int],
        total_questions: int,
    ) -> Dict[str, Any]:
        return await asyncio.to_thread(
            self._save_answer_submission_sync,
            registration,
            answers_text,
            correct_count,
            total_questions,
        )

    def _save_answer_submission_sync(
        self,
        registration: Dict[str, Any],
        answers_text: str,
        correct_count: Optional[int],
        total_questions: int,
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat(timespec="seconds")
        checked_at = now if correct_count is not None else None
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO answer_submissions (
                    registration_id, telegram_id, participant_code, answers_text,
                    correct_count, total_questions, checked_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    registration_id = excluded.registration_id,
                    participant_code = excluded.participant_code,
                    answers_text = excluded.answers_text,
                    correct_count = excluded.correct_count,
                    total_questions = excluded.total_questions,
                    checked_at = excluded.checked_at,
                    updated_at = excluded.updated_at
                """,
                (
                    registration["id"],
                    registration["telegram_id"],
                    registration["participant_code"],
                    answers_text,
                    correct_count,
                    total_questions,
                    checked_at,
                    now,
                    now,
                ),
            )
            row = connection.execute(
                """
                SELECT s.*, r.student_full_name, r.grade, r.olympiad_location
                FROM answer_submissions s
                JOIN registrations r ON r.id = s.registration_id
                WHERE s.telegram_id = ?
                """,
                (registration["telegram_id"],),
            ).fetchone()
        return dict(row)

    async def all_answer_submissions(self) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._all_answer_submissions_sync)

    def _all_answer_submissions_sync(self) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.*, r.student_full_name, r.grade, r.olympiad_location
                FROM answer_submissions s
                JOIN registrations r ON r.id = s.registration_id
                ORDER BY
                    s.correct_count IS NULL ASC,
                    s.correct_count DESC,
                    s.updated_at ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    async def update_answer_submission_score(
        self, submission_id: int, correct_count: int
    ) -> None:
        await asyncio.to_thread(
            self._update_answer_submission_score_sync,
            submission_id,
            correct_count,
        )

    def _update_answer_submission_score_sync(
        self, submission_id: int, correct_count: int
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE answer_submissions
                SET correct_count = ?, checked_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (correct_count, now, now, submission_id),
            )

    async def export_answer_submissions_csv(self) -> bytes:
        rows = await self.all_answer_submissions()
        output = io.StringIO()
        output.write("\ufeff")
        writer = csv.DictWriter(output, fieldnames=ANSWER_SUBMISSION_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {column: row.get(column, "") for column in ANSWER_SUBMISSION_COLUMNS}
            )
        return output.getvalue().encode("utf-8")
