odoo.define("point_of_sale.CreateOrderButton", function (require) {
    "use strict";

    const PosComponent = require("point_of_sale.PosComponent");
    const ProductScreen = require("point_of_sale.ProductScreen");
    const Registries = require("point_of_sale.Registries");

    class CreateOrderButton extends PosComponent {
        async onClick() {
            await this.showPopup("CreateOrderPopup", {});
        }
    }

    CreateOrderButton.template = "CreateOrderButton";

    ProductScreen.addControlButton({
        component: CreateOrderButton,
        // Static visibility: the button shows whenever the feature is enabled.
        condition: function () {
            return this.env.pos.config.iface_create_sale_order;
        },
        // Dynamic state: visible but disabled while a customer or an order line
        // is missing, so the cashier sees what is left to create the order.
        disabled: function () {
            const order = this.env.pos.get_order();
            if (!order) {
                return true;
            }
            return !order.get_partner() || order.get_orderlines().length === 0;
        },
        disabledReason: function () {
            const order = this.env.pos.get_order();
            if (order && !order.get_partner()) {
                return this.env._t("Add a customer to create the sale order.");
            }
            return this.env._t("Add at least one line to create the sale order.");
        },
    });

    Registries.Component.add(CreateOrderButton);

    return CreateOrderButton;
});
