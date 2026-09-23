from odoo import _, api, models

from odoo.addons.queue_job.job import Job, identity_exact


class StockNotifierPosMixin(models.AbstractModel):
    _name = "stock.notifier.pos.mixin"
    _description = "Stock Notifier POS Mixin"

    PRECOMMIT_BUFFER_KEY = "pos_stock_available_online.notify_buffer"
    ENQUEUED_JOBS_KEY = "pos_stock_available_online.enqueued_jobs"

    def _skip_notify_pos(self):
        """
        Skip notification to POS
        """
        return False

    def _get_warehouses_to_notify(self):
        self.ensure_one()
        return self.env["stock.warehouse"]

    def _notify_pos(self):
        """Only identifiers are buffered, never quantities: the quantity is
        computed inside the job over the final state, because the POS keeps
        the last message it receives for a product."""
        pairs = set()
        for record in self:
            if record._skip_notify_pos():
                continue
            product = record.product_id
            if not product:
                continue
            for warehouse in record._get_warehouses_to_notify():
                pairs.add((warehouse.id, product.id))
        if not pairs:
            return
        cr = self.env.cr
        buffer = cr.precommit.data.get(self.PRECOMMIT_BUFFER_KEY)
        if buffer is None:
            buffer = cr.precommit.data[self.PRECOMMIT_BUFFER_KEY] = set()
            cr.precommit.add(
                self.env["stock.notifier.pos.mixin"]._flush_notify_pos_buffer
            )
        buffer |= pairs

    @api.model
    def _flush_notify_pos_buffer(self):
        pairs = self.env.cr.precommit.data.pop(self.PRECOMMIT_BUFFER_KEY, None)
        if not pairs or not self._has_pos_listening_to_stock():
            return
        enqueued = self.env.cr.postcommit.data.setdefault(self.ENQUEUED_JOBS_KEY, {})
        pairs = self._pairs_without_job_in_transaction(pairs, enqueued)
        products_by_warehouse = {}
        for warehouse_id, product_id in pairs:
            products_by_warehouse.setdefault(warehouse_id, set()).add(product_id)
        notifier = self.env["stock.notifier.pos.mixin"].sudo()
        for warehouse_id, product_ids in products_by_warehouse.items():
            job = notifier.with_delay(
                description=_("Updating stock of %s products on the POS")
                % len(product_ids),
                channel="root.pos_stock_notification",
                identity_key=identity_exact,
            ).notify_available_quantity_to_pos_batch(warehouse_id, sorted(product_ids))
            if isinstance(job, Job):
                enqueued.update(
                    {(warehouse_id, product_id): job.uuid for product_id in product_ids}
                )

    @api.model
    def _pairs_without_job_in_transaction(self, pairs, enqueued):
        """Savepoints flush the buffer, so one transaction can reach here
        several times. A job created in it runs only after the commit and reads
        the final state, so its pairs need no other job; the lookup skips jobs
        a savepoint rollback has removed. Jobs reused through identity_key come
        from earlier transactions and may already be running, so they are not
        recorded."""
        uuids = {enqueued[pair] for pair in pairs if pair in enqueued}
        if not uuids:
            return pairs
        alive = set(
            self.env["queue.job"]
            .sudo()
            .search([("uuid", "in", list(uuids))])
            .mapped("uuid")
        )
        return {pair for pair in pairs if enqueued.get(pair) not in alive}

    @api.model
    def _has_pos_listening_to_stock(self):
        return bool(
            self.env["pos.session"]
            .sudo()
            .search_count(
                [
                    ("state", "=", "opened"),
                    ("config_id.display_product_quantity", "=", True),
                ],
                limit=1,
            )
        )

    @api.model
    def notify_available_quantity_to_pos_batch(self, warehouse_id, product_ids):
        warehouse = self.env["stock.warehouse"].browse(warehouse_id).exists()
        products = self.env["product.product"].browse(product_ids).exists()
        if not warehouse or not products:
            return
        configs = (
            self.env["pos.session"]
            .search(
                [
                    ("state", "=", "opened"),
                    ("config_id.display_product_quantity", "=", True),
                    "|",
                    ("config_id.additional_warehouse_ids", "in", [warehouse.id]),
                    ("config_id.main_warehouse_id", "=", warehouse.id),
                ],
            )
            .mapped("config_id")
        )
        if not configs:
            return
        for product in products:
            categ_id = product.pos_categ_id.id
            targets = configs.filtered(
                lambda config: not config.iface_available_categ_ids
                or categ_id in config.iface_available_categ_ids.ids
            )
            if targets:
                targets._notify_available_quantity(
                    warehouse._prepare_vals_for_pos(product)
                )

    @api.model
    def notify_available_quantity_to_pos(self, configs, warehouse, product_id):
        """Kept for the jobs enqueued before the upgrade, which reference it
        by name."""
        configs._notify_available_quantity(warehouse._prepare_vals_for_pos(product_id))
