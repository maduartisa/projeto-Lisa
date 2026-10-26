import unittest

from stacks.stage_config import StageConfig


class StageConfigTest(unittest.TestCase):
    def test_production_uses_high_availability_defaults(self) -> None:
        config = StageConfig.for_name("prod")

        self.assertEqual(config.nat_gateways, 2)
        self.assertTrue(config.database_multi_az)
        self.assertEqual(config.backup_retention_days, 30)

    def test_unknown_environment_fails_explicitly(self) -> None:
        with self.assertRaisesRegex(ValueError, "Ambiente desconhecido"):
            StageConfig.for_name("production-ish")


if __name__ == "__main__":
    unittest.main()
