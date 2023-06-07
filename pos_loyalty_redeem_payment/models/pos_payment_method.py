from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    used_for_loyalty_program = fields.Boolean(
        string="Used for loyalty program",
        compute="_compute_used_for_loyalty_program",
        readonly=True,
        store=True,
        help="In PoS interface, this method allows to redeem a gift card.",
    )
    program_id = fields.Many2one("loyalty.program")

    @api.depends("program_id")
    def _compute_used_for_loyalty_program(self):
        for rec in self:
            rec.used_for_loyalty_program = bool(rec.program_id)
