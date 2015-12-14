# -*- coding: utf-8 -*-
# © 2015 FactorLibre - Ismael Calvo <ismael.calvo@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, api, fields


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_return = fields.Boolean('Is return', default=False)

    @api.model
    def create(self, vals):
        res = super(PosOrder, self).create(vals)
        if res.amount_total < 0:
            res.write({'is_return': True})
        return res

    @api.model
    def search_orders_to_return(self, query):
        condition = [
            ('is_return', '=', False),
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('statement_ids', '!=', False),
            '|', '|',
            ('name', 'ilike', query),
            ('partner_id', 'ilike', query),
            ('pos_reference', 'ilike', query)
        ]
        fields = ['name', 'pos_reference', 'date_order', 'partner_id',
                  'amount_total']
        return self.search_read(condition, fields)

    @api.one
    def load_order(self):
        condition = [('order_id', '=', self.id)]
        fields = ['product_id', 'price_unit', 'qty', 'discount']
        orderlines = self.lines.search_read(condition, fields)
        return {
            'id': self.id,
            'name': self.pos_reference,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'orderlines': orderlines
        }

    @api.one
    def load_return_order(self):
        return_order_id = self.refund()['res_id']
        return_order = self.browse(return_order_id)
        condition = [('order_id', '=', return_order_id)]
        fields = ['product_id', 'price_unit', 'qty', 'discount']
        orderlines = self.lines.search_read(condition, fields)
        return {
            'id': return_order.id,
            'name': return_order.pos_reference,
            'partner_id': return_order.partner_id and
            return_order.partner_id.id or False,
            'orderlines': orderlines
        }
