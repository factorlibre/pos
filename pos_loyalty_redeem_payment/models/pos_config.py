# © 2023 FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    return_voucher = fields.Boolean(default=False)

    def assign_payment_journals(self, company):
        result = super().assign_payment_journals(company)
        for pos_config in self:
            payment_methods = self.env["pos.payment.method"]
            bank_journal = self.company_id.voucher_journal_id
            payment_method = payment_methods.create(
                {
                    "name": _("Vouchers"),
                    "company_id": company.id,
                    "is_voucher": True,
                    "journal_id": bank_journal.id,
                }
            )
            pos_config.write({"payment_method_ids": [(4, payment_method.id)]})
        return result

    def get_gift_card_programs(self):
        all_programs = self._get_program_ids()
        filtered_programs = all_programs.filtered(
            lambda x: x.program_type == "gift_card"
        )
        return filtered_programs

    def use_coupon_code(self, code, creation_date, partner_id):
        self.ensure_one()
        result = super().use_coupon_code(code, creation_date, partner_id)
        if not result.get("successful"):
            return result
        paymethod_id = self.env.context.get("payment_method_id")
        coupon = self.env["loyalty.card"].search(
            [
                ("program_id", "in", self.get_gift_card_programs().ids),
                ("code", "=", code),
            ],
            order="partner_id, points desc",
            limit=1,
        )
        # FROM PAYMENT_SCREEN
        if paymethod_id:
            valid_coupon = coupon.filtered(
                lambda x: paymethod_id in x.program_id.pos_payment_method_ids.ids
                and x.program_id.redeem_method == "payment_method"
            )
            if not valid_coupon:
                return {
                    "successful": False,
                    "payload": {
                        "error_message": _(
                            "Coupon ({}) must be redeemed from 'Insert Code' of product screen."
                        ).format(code, coupon.program_id.name),
                    },
                }
            return result
        # FROM ORDER SCREEN
        if coupon and coupon.program_id.redeem_method == "payment_method":
            return {
                "successful": False,
                "payload": {
                    "error_message": _(
                        "Coupon ({}) must be redeemed from payment screen."
                    ).format(code, coupon.program_id.name),
                },
            }
        return result
