import unittest

from core import input_mapping


class InputMappingTest(unittest.TestCase):
    def test_axis_scaling_matches_xinput_range(self) -> None:
        self.assertEqual(input_mapping.scale_axis_0_255_to_x360(128), 0)
        self.assertEqual(input_mapping.scale_axis_0_255_to_x360(255), 32767)
        self.assertEqual(input_mapping.scale_axis_0_255_to_x360(0), -32768)
        self.assertEqual(input_mapping.scale_axis_0_255_to_x360(255, invert=True), -32767)

    def test_deadzone_centers_small_offsets(self) -> None:
        self.assertEqual(input_mapping.apply_deadzone(132, 127, 0.1, (False, False)), (0, 0))

    def test_decodes_masked_buttons(self) -> None:
        report = [0x00, 0x20, 0x00]

        self.assertTrue(input_mapping.get_button_state(report, {"byte": 1, "mask": "0x20"}))
        self.assertFalse(input_mapping.get_button_state(report, {"byte": 1, "mask": "0x40"}))
        self.assertFalse(input_mapping.get_button_state(report, {"byte": 99, "mask": "0x20"}))

    def test_decodes_hat_switch_directions(self) -> None:
        report = [0x01, 0x05, 0x08]

        self.assertEqual(
            input_mapping.get_dpad_from_hat(report, {"byte": 0, "mask": "0x0F"}),
            (True, False, False, True),
        )
        self.assertEqual(
            input_mapping.get_dpad_from_hat(report, {"byte": 1, "mask": "0x0F"}),
            (False, True, True, False),
        )
        self.assertEqual(
            input_mapping.get_dpad_from_hat(report, {"byte": 2, "mask": "0x0F"}),
            (False, False, False, False),
        )


if __name__ == "__main__":
    unittest.main()
