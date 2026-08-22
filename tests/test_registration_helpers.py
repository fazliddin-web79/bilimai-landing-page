import unittest

from bot.utils import clean_text, normalize_phone, parse_answer_text, score_answers


class RegistrationHelperTests(unittest.TestCase):
    def test_normalize_uzbek_phone_formats(self) -> None:
        self.assertEqual(normalize_phone("+998 90 123 45 67"), "+998901234567")
        self.assertEqual(normalize_phone("90 123 45 67"), "+998901234567")
        self.assertEqual(normalize_phone("8 90 123 45 67"), "+998901234567")

    def test_invalid_phone_raises_clear_error(self) -> None:
        with self.assertRaises(ValueError):
            normalize_phone("123")

    def test_clean_text_collapses_spaces_and_limits_length(self) -> None:
        self.assertEqual(clean_text("  Ali   Valiyev  "), "Ali Valiyev")
        self.assertEqual(clean_text("abcdef", 3), "abc")

    def test_parse_answer_text_accepts_30_numbered_answers(self) -> None:
        answers = "".join(
            f"{index}{'ABCD'[(index - 1) % 4]}" for index in range(1, 31)
        )

        self.assertEqual(parse_answer_text(answers), answers)

    def test_parse_answer_text_rejects_missing_question(self) -> None:
        with self.assertRaises(ValueError):
            parse_answer_text("1A2B3C")

    def test_score_answers_counts_correct_and_wrong_questions(self) -> None:
        key = "".join(f"{index}A" for index in range(1, 31))
        submitted = "1B" + "".join(f"{index}A" for index in range(2, 31))

        correct, wrong = score_answers(submitted, key)

        self.assertEqual(correct, 29)
        self.assertEqual(wrong, [1])


if __name__ == "__main__":
    unittest.main()
