# © 2023 FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Pos Loyalty Redeem Payment",
    "summary": "Use vouchers as payment method in pos orders",
    "category": "Point Of Sale & Sales",
    "version": "16.0.2.0.0",
    "website": "https://git.factorlibre.com/odoo-16/pos",
    "author": "FactorLibre",
    "application": False,
    "depends": [
        "pos_loyalty_partial_redeem",
        "pos_loyalty_info_fields",
        "pos_vouchers",
        "pos_order_ticket",
    ],
    "data": [
        "views/pos_payment_method_views.xml",
        "views/loyalty_program_views.xml",
    ],
    "assets": {
        "point_of_sale.assets": [
            "pos_loyalty_redeem_payment/static/src/js/**/*",
            "pos_loyalty_redeem_payment/static/src/xml/**/*",
        ],
        "web.assets_tests": [
            "pos_loyalty_redeem_payment/static/tests/tours/**/*",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
