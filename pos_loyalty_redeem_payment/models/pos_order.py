# © 2023 FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models
from odoo.osv import expression


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.depends("payment_ids.coupon_id")
    def _compute_coupon_ids(self):
        super()._compute_coupon_ids()
        for record in self:
            record.coupon_ids |= record.payment_ids.mapped("coupon_id")
        return

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        fields = super(PosOrder, self)._payment_fields(order, ui_paymentline)
        if not ui_paymentline.get("coupon_data"):
            return fields
        coupon_id = ui_paymentline.get("coupon_data").get("coupon", {}).get("coupon_id")
        fields.update({"coupon_id": coupon_id})
        return fields

    def apply_redeem_amount(self, coupons_data):
        for coupon_id, amount in coupons_data.items():
            card = self.env["loyalty.card"].browse(coupon_id)
            if card:
                total = card.points - amount
                card.points = total

    def retrieve_coupon_data(self, order):
        if order:
            payments = [
                payment[2] for payment in order.get("data", {}).get("statement_ids", {})
            ]
            coupons_data = {
                e.get("coupon").get("coupon_id"): e.get("amount")
                for e in list(map(lambda x: x.get("coupon_data"), payments))
                if e
            }
            return coupons_data

    @api.model
    def _process_order(self, order, draft, existing_order):
        order_id = super()._process_order(order, draft, existing_order)
        order_db = self.browse(order_id)

        is_redeem_code = order_db.payment_ids.filtered(
            lambda x: x.payment_method_id.redeem_code
        )
        if order_db.amount_total > 0 and is_redeem_code:
            data = self.retrieve_coupon_data(order)
            self.apply_redeem_amount(data)
        return order_id

    @api.model
    def get_voucher_from_order(self, order_ids, extra_domain=None):
        domain = expression.OR([[("used_order_ids", "in", order_ids)], extra_domain])
        return super(PosOrder, self).get_voucher_from_order(order_ids, domain)
