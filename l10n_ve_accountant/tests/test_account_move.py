import logging
import datetime
from odoo.tests import TransactionCase, tagged
from odoo import fields, Command
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

@tagged("post_install", "-at_install", "l10n_ve_accountant")
class TestAccountMove(TransactionCase):

    def setUp(self):
        super(TestAccountMove, self).setUp()
        self.currency_usd = self.env.ref("base.USD")
        self.currency_vef = self.env.ref("base.VEF")
        self.company = self.env.ref("base.main_company")
        self.company.write(
            {
                "currency_id": self.currency_vef.id,
                "currency_foreign_id": self.currency_usd.id,
            }
        )

        self.tax_iva16 = self.env['account.tax'].create({
            'name': 'IVA 16%',
            'amount': 16,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        self.product = self.env['product.product'].create({
            'name': 'Producto Prueba',
            'type': 'service',
            'list_price': 100,
            'barcode': '123456789',
            'taxes_id': [(6, 0, [self.tax_iva16.id])],
        })
        
        self.partner_a = self.env['res.partner'].create({
            'name': 'Test Partner A',
            'customer_rank': 1,
        })
        
        self.company_data = {
            'company': self.env['res.company'].create({
                'name': 'Test Company',
                'currency_id': self.env.ref('base.VEF').id,
            }),
        }
        sequence = self.env['ir.sequence'].create({
            'name': 'Secuencia Factura',
            'code': 'account.move',
            'prefix': 'INV/',
            'padding': 8,
            "number_next_actual": 2,
        })
        refund_sequence = self.env['ir.sequence'].create({
            'name': 'nota de credito',
            'code': '',
            'prefix': 'NC/',
            'padding': 8,
            "number_next_actual": 2,
        })

        self.journal = self.env['account.journal'].create({
            'name': 'Diario de Ventas',
            'code': 'VEN',
            'type': 'sale',
            'company_id': self.env.company.id,
        })

    def _create_invoice(
            self, 
            products, 
            move_type="out_invoice", 
            reversed_entry_id=None, 
            debit_origin_id=None, 
            ref = "Test Invoice",
            foreign_rate=38,
            foreign_inverse_rate=38,
            invoice_date=None
        ):
        """Helper function to create an invoice with given parameters.
        Args:
            products (list): List of dictionaries with product details.
            foreign_rate (float): Foreign exchange rate.
            foreign_inverse_rate (float): Inverse foreign exchange rate.
        """
        invoice_lines = [
            Command.create(
                {
                    "product_id": product["product_id"],
                    "quantity": product.get("quantity", 1),
                    "price_unit": product["price_unit"],
                    "tax_ids": product.get("tax_ids", []),
                }
            )
            for product in products
        ]

        invoice_vals = {
            "move_type": move_type,
            "partner_id": self.partner_a.id,
            "foreign_currency_id": self.currency_usd.id,
            "currency_id": self.currency_vef.id,
            "state": "draft",
            "foreign_rate": foreign_rate,
            "foreign_inverse_rate": foreign_inverse_rate,
            "manually_set_rate": True,
            "invoice_line_ids": invoice_lines,
            "invoice_date": fields.Date.today(),
            "journal_id": self.journal.id,
        }

        # Solo para notas de crédito
        if move_type == "out_refund" and reversed_entry_id:
            invoice_vals["reversed_entry_id"] = reversed_entry_id.id
            invoice_vals["ref"] = ref

        if move_type == "out_invoice" and debit_origin_id:
            invoice_vals["debit_origin_id"] = debit_origin_id.id
            invoice_vals["ref"] = ref
        
        invoice = self.env["account.move"].create(invoice_vals)

        return invoice

    def test_01_create_invoice(self):
        """Test the creation and posting of an invoice with foreign currency."""
        products = [
            {
                "product_id": self.product.id,
                "price_unit": 100,
                "tax_ids": [(6, 0, [self.tax_iva16.id])],
            }
        ]
        invoice = self._create_invoice(products)
        invoice.write(
            {
                "currency_id": self.currency_usd.id,
            }
        )
        invoice.with_context(move_action_post_alert=True).action_post()
        self.assertEqual(invoice.state, "posted")
        _logger.info("test_01_create_invoice --- successfully.")
