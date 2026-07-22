/** @odoo-module **/
/*
    Copyright (C) 2022-Today GRAP (http://www.grap.coop)
    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
*/

import {getSteps, startSteps} from "point_of_sale.tour.utils";
import {PosOrderToSaleOrder} from "./helpers/PosOrderToSaleOrderMethods.esm";
import {ProductScreen} from "point_of_sale.tour.ProductScreenTourMethods";
import Tour from "web_tour.tour";

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

// V2: with no customer set, the button is visible but disabled and the tooltip
// asks for a customer.
getSteps().push({
    content: "Create Order button is disabled while no customer is set",
    trigger:
        ".o_control_button_wrapper.o_disabled" +
        "[title='Add a customer to create the sale order.']" +
        " .control-button span:contains('Create Order')",
    run: function () {}, // eslint-disable-line no-empty-function
});

// Set a customer (the cart is still empty).
ProductScreen.do.clickPartnerButton();
ProductScreen.do.clickCustomer("Addison Olson");

// V3: with a customer but an empty cart, the button stays disabled and the
// tooltip now asks for a line.
getSteps().push({
    content: "Create Order button is disabled while the cart is empty",
    trigger:
        ".o_control_button_wrapper.o_disabled" +
        "[title='Add at least one line to create the sale order.']" +
        " .control-button span:contains('Create Order')",
    run: function () {}, // eslint-disable-line no-empty-function
});

// Add an order line: now there is a customer and at least one line.
ProductScreen.exec.addOrderline("Whiteboard Pen", "1");

// V4: the button becomes enabled reactively (wrapper loses .o_disabled).
getSteps().push({
    content: "Create Order button is enabled once customer and line are set",
    trigger:
        ".o_control_button_wrapper:not(.o_disabled)" +
        " .control-button span:contains('Create Order')",
    run: function () {}, // eslint-disable-line no-empty-function
});

// V5: clicking the enabled button opens the creation popup unchanged.
PosOrderToSaleOrder.do.clickCreateOrderButton();
getSteps().push({
    content: "The create sale order popup is shown",
    trigger: ".popup-create-sale-order",
    run: function () {}, // eslint-disable-line no-empty-function
});

Tour.register(
    "PosOrderToSaleOrderDisabledTour",
    {test: true, url: "/pos/ui"},
    getSteps()
);
