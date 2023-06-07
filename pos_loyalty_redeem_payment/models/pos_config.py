from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _get_program_ids(self):
        ret = super()._get_program_ids()
        if self.env.context.get("payment_method_id"):
            return self.env["loyalty.program"].search(
                [
                    ("program_type", "=", "gift_card"),
                    ("id", "in", ret.ids),
                    ("redeem_method", "=", "payment_method"),
                    (
                        "pos_payment_method_ids",
                        "in",
                        self.env.context.get("payment_method_id"),
                    ),
                ]
            )
        return ret
