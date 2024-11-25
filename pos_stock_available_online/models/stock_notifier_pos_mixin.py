from odoo import _, api, models


class StockNotifierPosMixin(models.AbstractModel):
    _name = "stock.notifier.pos.mixin"
    _description = "Stock Notifier POS Mixin"

    def _prepare_pos_message(self, warehouse=None):
        """Return prepared message to send to POS"""
        self.ensure_one()
        warehouse = warehouse or self.warehouse_id
        return warehouse._prepare_vals_for_pos(self.product_id)

    def _skip_notify_pos(self):
        """Skip notification to POS"""
        return False

    def _get_warehouses_to_notify(self):
        self.ensure_one()
        return self.warehouse_id

    def _notify_pos(self, batch_size=100):
        """Send notification to POS in batches"""
        pos_session_obj = self.env["pos.session"]
        products_by_warehouse = {}

        for record in self:
            if record._skip_notify_pos():
                continue
            for warehouse in self._get_warehouses_to_notify():
                if warehouse not in products_by_warehouse:
                    products_by_warehouse[warehouse] = []
                products_by_warehouse[warehouse].append(record.product_id)

        # TODO REVISAR CREAR POR LOTES
        for warehouse, products in products_by_warehouse.items():
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
                        [p.pos_categ_id.id for p in products],
                    ),
                ]
            ).mapped("config_id")

            if configs:
                self._create_batch_jobs(configs, warehouse, products, batch_size)

    def _create_batch_jobs(self, configs, warehouse, products, batch_size):
        """Create batch jobs for stock notification"""
        for i in range(0, len(products), batch_size):
            batch = products[i : i + batch_size]
            identity_key = f"stock_notify_batch_{warehouse.id}_{i}"
            description = _(
                "Updating stock for products batch %(start)d-%(end)d in warehouse %(warehouse)s"
            ) % {
                "start": i,
                "end": i + len(batch),
                "warehouse": warehouse.name,
            }
            self.env[self._name].with_delay(
                description=description,
                channel="root.pos_stock_notification",
                identity_key=identity_key,
            ).notify_batch_to_pos(configs, warehouse, batch)

    @api.model
    def notify_batch_to_pos(self, configs, warehouse, products):
        """Notify stock for a batch of products"""
        for product in products:
            configs._notify_available_quantity(warehouse._prepare_vals_for_pos(product))

    @api.model
    def notify_available_quantity_to_pos(self, configs, warehouse, product_id):
        """Individual product notification method (kept for compatibility)"""
        configs._notify_available_quantity(warehouse._prepare_vals_for_pos(product_id))
