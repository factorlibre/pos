# -*- coding: utf-8 -*-
# © 2015 FactorLibre - Ismael Calvo <ismael.calvo@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "POS Return Products",
    "version": "8.0.0.1.0",
    "author": "FactorLibre, Odoo Community Association (OCA)",
    "website": "http://www.factorlibre.com",
    "license": "AGPL-3",
    "category": "Point Of Sale",
    "depends": [
        'point_of_sale',
        'pos_sub_menu_widget'
    ],
    'data': [
        "views/pos_return_products.xml",
    ],
    "qweb": [
        'static/src/xml/pos_return_products.xml',
    ],
    "installable": True,
}
