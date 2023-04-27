# © 2023 FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    redeem_code = fields.Boolean(
        "Redemption Code",
        compute="_compute_redeem_code",
        readonly=True,
        store=True,
        help="In PoS interface, It allows to set a coupon as a payment method.",
    )
    program_id = fields.Many2one("loyalty.program")

    @api.depends("program_id")
    def _compute_redeem_code(self):
        for rec in self:
            rec.redeem_code = False if not rec.program_id else True
