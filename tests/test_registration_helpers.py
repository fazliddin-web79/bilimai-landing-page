import unittest

from bot.utils import clean_text, normalize_phone


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


if __name__ == "__main__":
    unittest.main()
