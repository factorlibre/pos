# © 2023 FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, fields, models


class LoyaltyProgram(models.Model):
    _inherit = "loyalty.program"

    def _default_redeem_method(self):
        return "payment_method" if self.is_voucher_program else "discount"

    redeem_method = fields.Selection(
        [("payment_method", "Payment Method"), ("discount", "Discount")],
        "Redemption Method",
        required=True,
        default=_default_redeem_method,
        help=""
        "Payment Method: The Voucher/Gift Card is used as a payment method in PoS orders.\n"
        "Discount: The Voucher/Gift Card is used as a discount.",
    )
    pos_payment_method_ids = fields.One2many(
        "pos.payment.method",
        "program_id",
        "POS Payment Methods",
        help="Payment methods related to this program.",
    )

    def write(self, vals):
        if "redeem_method" in vals and vals.get("redeem_method") == "discount":
            vals["pos_payment_method_ids"] = [Command.set([])]
        return super().write(vals)

    @api.onchange("is_voucher_program")
    def _onchange_is_voucher_program(self):
        self.redeem_method = "payment_method" if self.is_voucher_program else "discount"
