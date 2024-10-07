from odoo import _, api, models

from odoo.addons.queue_job.job import identity_exact


class StockNotifierPosMixin(models.AbstractModel):
    _name = "stock.notifier.pos.mixin"
    _description = "Stock Notifier POS Mixin"

    def _prepare_pos_message(self, warehouse=None):
        """
        Return prepared message to send to POS
        """
        self.ensure_one()
        warehouse = warehouse or self.warehouse_id
        return warehouse._prepare_vals_for_pos(self.product_id)

    def _skip_notify_pos(self):
        """
        Skip notification to POS
        """
        return False

    def _get_warehouses_to_notify(self):
        self.ensure_one()
        return self.warehouse_id

    def _notify_pos(self):
        """
        Send notification to POS
        """
        pos_session_obj = self.env["pos.session"]
        for record in self:
            if record._skip_notify_pos():
                continue
            for warehouse in self._get_warehouses_to_notify():
                configs = pos_session_obj.search(
                    [
                        ("state", "=", "opened"),
                        ("config_id.display_product_quantity", "=", True),
                        "|",
                        ("config_id.additional_warehouse_ids", "in", [warehouse.id]),
                        ("config_id.main_warehouse_id", "=", warehouse.id),
                        "|",
                        ("config_id.iface_available_categ_ids", "=", False),
                        (
                            "config_id.iface_available_categ_ids",
                            "in",
                            [record.product_id.pos_categ_id.id],
                        ),
                    ],
                ).mapped("config_id")
                if configs:
                    description = _(
                        "Updating stock of product %s in warehouse %s on the POS"
                    ) % (
                        record.product_id.name,
                        warehouse.name,
                    )

                    self.env[self._name].with_delay(
                        description=description,
                        channel="root.pos_stock_notification",
                        identity_key=identity_exact,
                    ).notify_available_quantity_to_pos(
                        configs, warehouse, record.product_id
                    )

    @api.model
    def notify_available_quantity_to_pos(self, configs, warehouse, product_id):
        configs._notify_available_quantity(warehouse._prepare_vals_for_pos(product_id))
