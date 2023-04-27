# © 2023 FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = "pos.session"

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result["search_params"]["fields"].extend(["redeem_code"])
        return result
