import unittest

from bot.registration import build_registration_input


class RegistrationFlowTests(unittest.TestCase):
    def test_state_data_becomes_registration_input(self) -> None:
        data = {
            "parent_full_name": "Aziz Karimov",
            "phone": "+998901234567",
            "student_full_name": "Ali Karimov",
            "grade": "2-sinf",
            "current_school": "10-maktab",
            "neighborhood": "Markaz",
            "olympiad_location": "3-IDUM",
            "source": "instagram",
        }

        registration = build_registration_input(123, "aziz", data)

        self.assertEqual(registration.telegram_id, 123)
        self.assertEqual(registration.telegram_username, "aziz")
        self.assertEqual(registration.student_full_name, "Ali Karimov")
        self.assertEqual(registration.olympiad_location, "3-IDUM")
        self.assertEqual(registration.source, "instagram")


if __name__ == "__main__":
    unittest.main()
