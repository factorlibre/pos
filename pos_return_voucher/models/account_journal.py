# -*- coding: utf-8 -*-
# © 2015 FactorLibre - Ismael Calvo <ismael.calvo@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields


class PosVoucher(models.Model):
    _inherit = 'account.journal'

    voucher_journal = fields.Boolean('Journal for vouchers', default=False)
