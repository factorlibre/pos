# Copyright 2024 Eugene Molotov (https://github.com/em230418)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    picking_creation_delayed = fields.Boolean(
        related="pos_config_id.picking_creation_delayed", readonly=False
    )

    @api.onchange("picking_creation_delayed", "update_stock_quantities")
    def _onchange_picking_creation_delayed(self):
        if self.picking_creation_delayed and self.update_stock_quantities == "closing":
            self.picking_creation_delayed = False
            return {
                "warning": {
                    "title": _("Picking Creation Delayed Warning"),
                    "message": _(
                        "The setting 'Picking Creation Delayed' is only compatible "
                        "with 'Inventory Management' in real time."
                    ),
                }
            }
