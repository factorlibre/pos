# -*- coding: utf-8 -*-
# © 2015 FactorLibre - Ismael Calvo <ismael.calvo@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields, api, exceptions, _
from datetime import datetime


class PosVoucher(models.Model):
    _name = 'pos.voucher'
    _description = 'POS Voucher'

    name = fields.Integer('Code', readonly=True, default=False)
    amount = fields.Float('Amount')
    due_date = fields.Date(
        'Due date',
        readonly=False)
    voucher_history_lines = fields.One2many(
        'pos.voucher.history_line',
        'voucher_id',
        'Voucher History',
        readonly=True)
    partner_id = fields.Many2one(
        'res.partner',
        'Partner')

    @api.model
    def create(self, vals):
        res = super(PosVoucher, self).create(vals)
        res.write({'name': res.id})
        return res

    @api.model
    def create_from_ui(self, vals):
        if 'amount' not in vals:
            raise exceptions.Warning(_('The amount is required'))
        new_voucher = self.create(vals)

        res = {
            'due_date': new_voucher.due_date,
            'amount': new_voucher.amount,
            'partner_id': new_voucher.partner_id or False,
            'name': new_voucher.name,
        }
        return res

    @api.model
    def search_vouchers(self, query='', partner_id=False):
        condition = []
        if query != '':
            condition += [
                '|',
                ('name', 'ilike', query),
                ('partner_id', 'ilike', query),
            ]
        else:
            condition += [
                ('due_date', '>=', datetime.today()),
                ('amount', '>', 0),
            ]
        if partner_id:
            condition.append(('partner_id', '=', partner_id))
        fields = ['due_date', 'name', 'amount', 'partner_id']
        res = self.search_read(condition, fields)
        return res

    @api.model
    def use_voucher(self, voucher_id, amount, new_due_date=None):
        voucher = self.browse(voucher_id)
        data = {'amount': voucher.amount - amount}
        if new_due_date:
            data.update({
                'due_date': new_due_date
            })
        return voucher.write(data)


class PosVoucherHistoryLine(models.Model):
    _name = 'pos.voucher.history_line'
    _description = 'POS Voucher History Line'

    amount = fields.Float('Amount', readonly=True)
    operation_type = fields.Selection([
        ('input', 'Input'),
        ('spend', 'Spend')
    ], 'Operation Type', readonly=True)
    date = fields.Date(
        'Date',
        readonly=True,
        default=fields.Date.today())
    pos_order_id = fields.Many2one(
        'pos.order',
        'Related Order',
        readonly=True)
    voucher_id = fields.Many2one(
        'pos.voucher',
        'Related Voucher',
        readonly=True)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    vouchers_expire = fields.Boolean('Vouchers Expire?', default=True)
    voucher_validity_period = fields.Integer(
        'Voucher Validity Period',
        help="(In days) Period of validity of a voucher. If a voucher is "
             "recharged, its due date is updated.",
        default=30)
