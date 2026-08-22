import tempfile
import unittest
from pathlib import Path

from bot.database import Database, DuplicateTelegramError, RegistrationInput


def sample_registration(**overrides):
    data = {
        "telegram_id": 7,
        "telegram_username": "aziz",
        "parent_full_name": "Aziz Karimov",
        "phone": "+998901234567",
        "student_full_name": "Ali Karimov",
        "grade": "2-sinf",
        "current_school": "10-maktab",
        "neighborhood": "Markaz",
        "olympiad_location": "3-IDUM",
        "source": "instagram",
    }
    data.update(overrides)
    return RegistrationInput(**data)


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(str(Path(self.temp_dir.name) / "test.db"))
        await self.database.initialize()

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def test_create_registration_assigns_participant_code(self) -> None:
        row = await self.database.create_registration(sample_registration())

        self.assertEqual(row["participant_code"], "AS-0001")
        self.assertEqual(row["student_full_name"], "Ali Karimov")
        self.assertEqual(row["attended"], 0)

    async def test_telegram_id_can_register_once(self) -> None:
        await self.database.create_registration(sample_registration())

        with self.assertRaises(DuplicateTelegramError):
            await self.database.create_registration(
                sample_registration(phone="+998901111111")
            )

    async def test_search_delete_attended_and_stats(self) -> None:
        await self.database.create_registration(sample_registration())
        await self.database.create_registration(
            sample_registration(
                telegram_id=8,
                telegram_username="malika",
                phone="+998901111111",
                student_full_name="Malika Olimova",
                grade="4-sinf",
                olympiad_location="13-maktab",
                source="telegram",
            )
        )

        results = await self.database.search("Malika")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["participant_code"], "AS-0002")

        attended = await self.database.mark_attended("AS-0002")
        self.assertIsNotNone(attended)
        self.assertEqual(attended["attended"], 1)

        stats = await self.database.stats()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["attended"], 1)
        self.assertEqual(stats["by_grade"]["4-sinf"], 1)
        self.assertEqual(stats["by_location"]["13-maktab"], 1)

        self.assertTrue(await self.database.delete_by_code("AS-0001"))
        self.assertIsNone(await self.database.get_by_code("AS-0001"))

    async def test_export_csv_has_utf8_bom(self) -> None:
        await self.database.create_registration(sample_registration())

        data = await self.database.export_csv()

        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        self.assertIn("participant_code", data.decode("utf-8"))

    async def test_answer_key_and_submission_are_saved(self) -> None:
        registration = await self.database.create_registration(sample_registration())
        answers = "".join(f"{index}A" for index in range(1, 31))

        key = await self.database.set_answer_key(answers)
        submission = await self.database.save_answer_submission(
            registration,
            answers,
            correct_count=30,
            total_questions=30,
        )

        self.assertEqual(key["answers_text"], answers)
        self.assertEqual(submission["participant_code"], "AS-0001")
        self.assertEqual(submission["correct_count"], 30)

        export = await self.database.export_answer_submissions_csv()
        self.assertTrue(export.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Ali Karimov", export.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
