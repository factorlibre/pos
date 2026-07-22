/** @odoo-module **/
/*
    Copyright (C) 2022-Today GRAP (http://www.grap.coop)
    License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
*/

import {getSteps, startSteps} from "point_of_sale.tour.utils";
import {ProductScreen} from "point_of_sale.tour.ProductScreenTourMethods";
import Tour from "web_tour.tour";

startSteps();

ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

// V1: when the feature is disabled (iface_create_sale_order == False) the button
// is not rendered at all, even though the control buttons container is present.
getSteps().push({
    content: "Create Order button is not rendered when the feature is disabled",
    trigger: ".product-screen .control-buttons",
    run: function () {
        const buttons = document.querySelectorAll(".control-buttons .control-button");
        const found = Array.from(buttons).some((button) =>
            button.textContent.includes("Create Order")
        );
        if (found) {
            throw new Error("Create Order button should not be rendered");
        }
    },
});

Tour.register(
    "PosOrderToSaleOrderHiddenTour",
    {test: true, url: "/pos/ui"},
    getSteps()
);
