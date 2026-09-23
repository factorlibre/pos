# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import json
import unittest
from unittest import mock

from odoo.tests import TransactionCase, tagged

from odoo.addons.queue_job.tests.common import trap_jobs

HOOK_QUERY_CEILING = 30


class RollbackSavepoint(Exception):
    pass


@tagged("post_install", "-at_install")
class TestStockNotifyBatch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Mixin = cls.env["stock.notifier.pos.mixin"]
        cls.warehouse = cls.env["stock.warehouse"].create(
            {"name": "Notify Batch WH", "code": "NBWH"}
        )
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")
        cls.customer_location = cls.env.ref("stock.stock_location_customers")

        cls.categ_a = cls.env["pos.category"].create({"name": "Notify Categ A"})
        cls.categ_b = cls.env["pos.category"].create({"name": "Notify Categ B"})
        cls.products_a = cls._create_products("A", 3, cls.categ_a)
        cls.products_b = cls._create_products("B", 2, cls.categ_b)

        cls.config_all = cls._create_config("Notify POS All", categories=None)
        cls.config_a = cls._create_config("Notify POS Only A", categories=cls.categ_a)
        cls.session_all = cls._open_session(cls.config_all)
        cls.session_a = cls._open_session(cls.config_a)

    @classmethod
    def _create_products(cls, suffix, count, categ):
        return cls.env["product.product"].create(
            [
                {
                    "name": "Notify Product %s%s" % (suffix, index),
                    "type": "product",
                    "available_in_pos": True,
                    "pos_categ_id": categ.id,
                }
                for index in range(count)
            ]
        )

    @classmethod
    def _create_config(cls, name, categories=None):
        values = {
            "name": name,
            "picking_type_id": cls.warehouse.out_type_id.id,
            "display_product_quantity": True,
        }
        if categories:
            values["iface_available_categ_ids"] = [(6, 0, categories.ids)]
        config = cls.env["pos.config"].create(values)
        assert config.main_warehouse_id == cls.warehouse
        return config

    @classmethod
    def _open_session(cls, config):
        session = cls.env["pos.session"].create(
            {"user_id": cls.env.uid, "config_id": config.id}
        )
        if session.state != "opened":
            session.action_pos_session_open()
        assert session.state == "opened"
        return session

    def _create_receipt(self, products, quantity=5.0):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom": product.uom_id.id,
                            "product_uom_qty": quantity,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.warehouse.lot_stock_id.id,
                        },
                    )
                    for product in products
                ],
            }
        )
        picking.action_confirm()
        return picking

    def _settle(self):
        """Stands for the commit that ends the previous transaction."""
        self.env.flush_all()
        self.env.cr.precommit.run()
        self.env.cr.postcommit.data.pop(self.Mixin.ENQUEUED_JOBS_KEY, None)

    def _validate(self, picking):
        for move in picking.move_ids:
            move.quantity_done = move.product_uom_qty
        picking.button_validate()
        self.env.cr.precommit.run()

    def _last_bus_id(self):
        last = self.env["bus.bus"].sudo().search([], order="id desc", limit=1)
        return last.id or 0

    def _bus_rows(self, min_id):
        rows = set()
        records = (
            self.env["bus.bus"].sudo().search([("id", ">", min_id)], order="id asc")
        )
        for record in records:
            channel = json.loads(record.channel)
            target = channel[1] if isinstance(channel, list) else channel
            if "pos_stock_available_online" not in str(target):
                continue
            payload = json.loads(record.message).get("payload") or []
            for item in payload:
                rows.add(
                    (
                        str(target),
                        item["id"],
                        item["product_id"],
                        item["quantity"],
                    )
                )
        return rows

    def _unbatched_configs_for(self, product):
        return (
            self.env["pos.session"]
            .sudo()
            .search(
                [
                    ("state", "=", "opened"),
                    ("config_id.display_product_quantity", "=", True),
                    "|",
                    (
                        "config_id.additional_warehouse_ids",
                        "in",
                        [self.warehouse.id],
                    ),
                    ("config_id.main_warehouse_id", "=", self.warehouse.id),
                    "|",
                    ("config_id.iface_available_categ_ids", "=", False),
                    (
                        "config_id.iface_available_categ_ids",
                        "in",
                        [product.pos_categ_id.id],
                    ),
                ],
            )
            .mapped("config_id")
        )

    def _emit_unbatched(self, products):
        for product in products:
            configs = self._unbatched_configs_for(product)
            if configs:
                self.Mixin.notify_available_quantity_to_pos(
                    configs, self.warehouse, product
                )

    def _jobs(self, trap):
        return [
            job
            for job in trap.enqueued_jobs
            if job.method_name == "notify_available_quantity_to_pos_batch"
        ]

    def _mark_stored_jobs_done(self):
        """Pending jobs would absorb the ones under test through identity_key;
        in production the runner has already processed them."""
        self.env["queue.job"].sudo().search([]).write({"state": "done"})

    def _last_stored_job_id(self):
        last = self.env["queue.job"].sudo().search([], order="id desc", limit=1)
        return last.id or 0

    def _stored_jobs_since(self, job_id):
        return (
            self.env["queue.job"]
            .sudo()
            .search(
                [
                    ("id", ">", job_id),
                    ("method_name", "=", "notify_available_quantity_to_pos_batch"),
                ]
            )
        )

    def _notified_product_ids(self, jobs):
        return {product_id for job in jobs for product_id in job.args[1]}

    def _measure_hook_queries(self, moves):
        """clear() and not run(): running would enqueue these pairs and
        identity_key would then dedupe the very enqueue being measured."""
        self.env.flush_all()
        self.env.cr.precommit.clear()
        before = self.env.cr.sql_log_count
        moves.sudo()._notify_pos()
        self.env.cr.precommit.run()
        return self.env.cr.sql_log_count - before

    def test_01_batch_matches_baseline(self):
        products = self.products_a | self.products_b
        picking = self._create_receipt(products)

        before_batched = self._last_bus_id()
        with trap_jobs() as trap:
            self._validate(picking)
            trap.perform_enqueued_jobs()
        batched = self._bus_rows(before_batched)

        before_reference = self._last_bus_id()
        self._emit_unbatched(products)
        reference = self._bus_rows(before_reference)

        self.assertTrue(reference)
        self.assertEqual(batched, reference)

    def test_01b_message_is_a_dict_per_product(self):
        """pos_stock_available_control reads the message as a bare dict and
        calls the method again per till, so only the outermost call counts."""
        picking = self._create_receipt(self.products_a)
        self._settle()
        received = []
        depth = []
        config_model = type(self.env["pos.config"])
        original = config_model._notify_available_quantity

        def _notify_available_quantity(records, message):
            if not depth:
                received.append(message)
            depth.append(message)
            try:
                return original(records, message)
            finally:
                depth.pop()

        with trap_jobs() as trap:
            self._validate(picking)
            with mock.patch.object(
                config_model, "_notify_available_quantity", _notify_available_quantity
            ):
                trap.perform_enqueued_jobs()
        self.assertEqual(len(received), len(self.products_a))
        for message in received:
            self.assertIsInstance(message, dict)
            self.assertIn("id", message)
            self.assertIn("product_id", message)

    def test_02_category_filter_excludes_product(self):
        products = self.products_a | self.products_b
        picking = self._create_receipt(products)

        before = self._last_bus_id()
        with trap_jobs() as trap:
            self._validate(picking)
            trap.perform_enqueued_jobs()
        rows = self._bus_rows(before)

        channel_a = self.config_a._get_channel_name()
        channel_all = self.config_all._get_channel_name()
        received_by_a = {row[2] for row in rows if row[0] == channel_a}
        received_by_all = {row[2] for row in rows if row[0] == channel_all}

        self.assertEqual(received_by_a, set(self.products_a.ids))
        self.assertEqual(received_by_all, set(products.ids))

    def test_03_query_count_ceiling(self):
        small = self._create_receipt(self.products_a, quantity=1.0)
        large = self._create_receipt(
            self._create_products("Q", 20, self.categ_a), quantity=1.0
        )
        self._settle()
        small_moves = small.move_ids
        large_moves = large.move_ids
        self.assertGreater(len(large_moves), len(small_moves))

        small_cost = self._measure_hook_queries(small_moves)
        large_cost = self._measure_hook_queries(large_moves)

        self.assertLessEqual(large_cost, HOOK_QUERY_CEILING)
        self.assertLessEqual(large_cost - small_cost, 2)

    def test_04_jobs_do_not_scale_with_lines(self):
        small = self._create_receipt(self.products_a)
        large = self._create_receipt(self.products_a | self.products_b)
        self._settle()

        with trap_jobs() as trap:
            self._validate(small)
            small_jobs = len(self._jobs(trap))
        with trap_jobs() as trap:
            self._validate(large)
            large_jobs = len(self._jobs(trap))

        self.assertGreaterEqual(small_jobs, 1)
        self.assertEqual(small_jobs, large_jobs)
        self.assertLess(large_jobs, len(large.move_ids))

    def test_05_two_validations_same_warehouse(self):
        first = self._create_receipt(self.products_a)
        second = self._create_receipt(self.products_b)
        self._settle()

        with trap_jobs() as trap:
            self._validate(first)
            self._validate(second)
            jobs = self._jobs(trap)

        self.assertEqual(len(jobs), 2)
        for job in jobs:
            self.assertTrue(job.identity_key)
        self.assertEqual(
            self._notified_product_ids(jobs),
            set((self.products_a | self.products_b).ids),
        )

    def test_06_no_open_session_short_circuits(self):
        for session in self.session_all | self.session_a:
            session.action_pos_session_closing_control()
            session.invalidate_recordset()
        still_open = (
            self.env["pos.session"]
            .sudo()
            .search_count(
                [
                    ("state", "=", "opened"),
                    ("config_id.display_product_quantity", "=", True),
                ]
            )
        )
        self.assertEqual(still_open, 0)
        picking = self._create_receipt(self.products_a)
        self._settle()

        with trap_jobs() as trap:
            self._validate(picking)
            self.assertEqual(len(self._jobs(trap)), 0)

    def test_07_reservation_path_not_regressed(self):
        products = self.products_a[:2]
        stock_location = self.warehouse.lot_stock_id
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": stock_location.id,
                "location_dest_id": self.customer_location.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom": product.uom_id.id,
                            "product_uom_qty": 1.0,
                            "location_id": stock_location.id,
                            "location_dest_id": self.customer_location.id,
                        },
                    )
                    for product in products
                ],
            }
        )
        picking.action_confirm()
        self.assertEqual(picking.state, "confirmed")
        for product in products:
            self.env["stock.quant"]._update_available_quantity(
                product, stock_location, 10.0
            )
        self._settle()
        self._mark_stored_jobs_done()
        last_job_id = self._last_stored_job_id()
        picking.action_assign()
        self.env.cr.precommit.run()
        jobs = self._stored_jobs_since(last_job_id)

        self.assertEqual(picking.state, "assigned")
        notified = sorted(product_id for job in jobs for product_id in job.args[1])
        self.assertEqual(notified, sorted(products.ids))

    def test_08_savepoint_rollback_keeps_prior_pairs(self):
        prior = self._create_receipt(self.products_a)
        inside = self._create_receipt(self.products_b)
        prior_moves = prior.move_ids
        inside_moves = inside.move_ids
        self._settle()

        with trap_jobs() as trap:
            prior_moves.sudo()._notify_pos()
            with self.assertRaises(ValueError):
                with self.env.cr.savepoint():
                    inside_moves.sudo()._notify_pos()
                    raise ValueError("rolled back on purpose")
            self.env.cr.precommit.run()
            notified = self._notified_product_ids(self._jobs(trap))

        self.assertTrue(set(self.products_a.ids).issubset(notified))
        self.assertFalse(set(self.products_b.ids) & notified)

    def test_09_flush_callback_registered_once(self):
        """Read on the private deque: identity_key hides duplicates in the job
        count and Callbacks has no public way to count pending callbacks."""
        first = self._create_receipt(self.products_a)
        second = self._create_receipt(self.products_b)
        self._settle()

        with trap_jobs() as trap:
            first.move_ids.sudo()._notify_pos()
            second.move_ids.sudo()._notify_pos()
            registered = [
                func
                for func in self.env.cr.precommit._funcs
                if getattr(func, "__name__", "") == "_flush_notify_pos_buffer"
            ]
            self.assertEqual(len(registered), 1)
            self.env.cr.precommit.run()
            self.assertEqual(len(self._jobs(trap)), 1)

    def _create_second_warehouse(self):
        return self.env["stock.warehouse"].create(
            {"name": "Notify Batch WH2", "code": "NBW2"}
        )

    def test_10_one_job_per_warehouse_touched(self):
        other = self._create_second_warehouse()
        product = self.products_a[0]
        source = self.warehouse.lot_stock_id
        destination = other.lot_stock_id
        self.env["stock.quant"]._update_available_quantity(product, source, 10.0)
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.int_type_id.id,
                "location_id": source.id,
                "location_dest_id": destination.id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom": product.uom_id.id,
                            "product_uom_qty": 1.0,
                            "location_id": source.id,
                            "location_dest_id": destination.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        picking.action_assign()
        self._settle()

        with trap_jobs() as trap:
            self._validate(picking)
            warehouse_ids = [job.args[0] for job in self._jobs(trap)]

        self.assertEqual(sorted(warehouse_ids), sorted([self.warehouse.id, other.id]))

    def test_11_additional_warehouse_till_receives_stock(self):
        other = self._create_second_warehouse()
        config = self.env["pos.config"].create(
            {
                "name": "Notify POS Additional",
                "picking_type_id": other.out_type_id.id,
                "display_product_quantity": True,
                "additional_warehouse_ids": [(6, 0, self.warehouse.ids)],
            }
        )
        self._open_session(config)
        picking = self._create_receipt(self.products_a)

        before = self._last_bus_id()
        with trap_jobs() as trap:
            self._validate(picking)
            trap.perform_enqueued_jobs()
        channel = config._get_channel_name()
        received = {row[2] for row in self._bus_rows(before) if row[0] == channel}

        self.assertEqual(received, set(self.products_a.ids))

    def test_12_product_without_category_reaches_only_unrestricted_tills(self):
        product = self.env["product.product"].create(
            {
                "name": "Notify Product Without Category",
                "type": "product",
                "available_in_pos": True,
            }
        )
        picking = self._create_receipt(product)

        before = self._last_bus_id()
        with trap_jobs() as trap:
            self._validate(picking)
            trap.perform_enqueued_jobs()
        receivers = {row[0] for row in self._bus_rows(before) if row[2] == product.id}

        self.assertEqual(receivers, {self.config_all._get_channel_name()})

    def test_13_quant_write_on_several_quants_notifies_them_all(self):
        stock_location = self.warehouse.lot_stock_id
        for product in self.products_a:
            self.env["stock.quant"]._update_available_quantity(
                product, stock_location, 5.0
            )
        quants = self.env["stock.quant"].search(
            [
                ("product_id", "in", self.products_a.ids),
                ("location_id", "=", stock_location.id),
            ]
        )
        self.assertEqual(len(quants), len(self.products_a))
        self._settle()

        with trap_jobs() as trap:
            quants.sudo().write({"quantity": 7.0})
            self.env.cr.precommit.run()
            jobs = self._jobs(trap)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(self._notified_product_ids(jobs), set(self.products_a.ids))

    def test_14_failed_flush_leaves_no_orphan_buffer(self):
        """Plain unittest assertRaises: Odoo's opens a savepoint, whose flush
        would run the failing callback before the context is entered."""
        moves = self._create_receipt(self.products_a).move_ids
        self._settle()
        mixin_class = type(self.Mixin)

        with mock.patch.object(
            mixin_class, "_has_pos_listening_to_stock", side_effect=RuntimeError
        ):
            moves.sudo()._notify_pos()
            with unittest.TestCase.assertRaises(self, RuntimeError):
                self.env.cr.precommit.run()

        self.assertNotIn(self.Mixin.PRECOMMIT_BUFFER_KEY, self.env.cr.precommit.data)
        self.env.cr.precommit.clear()

    def test_15_stock_user_without_pos_rights_notifies_tills(self):
        user = self.env["res.users"].create(
            {
                "name": "Notify Stock User",
                "login": "notify_stock_user",
                "groups_id": [(6, 0, [self.env.ref("stock.group_stock_user").id])],
            }
        )
        self.assertFalse(user.has_group("point_of_sale.group_pos_user"))
        picking = self._create_receipt(self.products_a)
        self._settle()

        before = self._last_bus_id()
        with trap_jobs() as trap:
            self._validate(picking.with_user(user))
            trap.perform_enqueued_jobs()
        channel = self.config_all._get_channel_name()
        received = {row[2] for row in self._bus_rows(before) if row[0] == channel}

        self.assertEqual(received, set(self.products_a.ids))

    def test_16_write_notifies_only_moves_whose_state_changed(self):
        picking = self._create_receipt(self.products_a[:2])
        changed, unchanged = picking.move_ids
        state = unchanged.state
        changed.write({"state": "draft"})
        self._settle()

        with trap_jobs() as trap:
            picking.move_ids.write({"state": state})
            self.env.cr.precommit.run()
            jobs = self._jobs(trap)

        self.assertEqual(self._notified_product_ids(jobs), {changed.product_id.id})
        self.assertNotEqual(changed.product_id, unchanged.product_id)

    def test_17_pair_whose_job_was_rolled_back_is_enqueued_again(self):
        moves = self._create_receipt(self.products_a[:1]).move_ids
        self._settle()
        self._mark_stored_jobs_done()
        last_job_id = self._last_stored_job_id()

        with self.assertRaises(RollbackSavepoint):
            with self.env.cr.savepoint():
                moves.sudo()._notify_pos()
                self.env.cr.precommit.run()
                self.assertTrue(self._stored_jobs_since(last_job_id))
                raise RollbackSavepoint
        moves.sudo()._notify_pos()
        self.env.cr.precommit.run()

        jobs = self._stored_jobs_since(last_job_id)
        self.assertEqual(self._notified_product_ids(jobs), set(moves.product_id.ids))
