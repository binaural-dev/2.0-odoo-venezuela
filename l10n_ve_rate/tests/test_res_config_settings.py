from odoo.exceptions import UserError
from odoo import fields, Command
from odoo.tests import TransactionCase, tagged
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

@tagged("post_install", "-at_install", "l10n_ve_rate") 
class TestResConfigSettings(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env.ref("base.main_company")
        self.currency_usd = self.env.ref("base.USD")
        self.currency_vef = self.env.ref("base.VEF")

    def test_01_default_currency_id_is_vef(self):
        config = self.env["res.config.settings"].new({})
        self.assertEqual(config.currency_id, self.currency_vef, "The default base currency must be VEF")
        _logger.info("test_01_default_currency_id_is_vef --- successfully.")

    def test_02_currency_foreign_id_equal_currency_id_raises(self):
        config = self.env["res.config.settings"].new({
            "company_id": self.company.id,
            "currency_id": self.currency_usd.id,
        })
        
        with self.assertRaises(UserError) as e:
            config._check_currency_id()
        _logger.info("Expected error: %s", e.exception)

        exception = "The company currency must be in bolivars. Please set the currency to Bolivar (VEF)."

        self.assertEqual(
            str(e.exception),
            exception,
            f"The error message should indicate that: {exception}",
        )

        _logger.info("test_02_currency_foreign_id_equal_currency_id_raises --- successfully.")
