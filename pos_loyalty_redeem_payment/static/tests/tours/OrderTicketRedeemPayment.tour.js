/** @odoo-module **/
/** © 2023 - FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). **/

import {getSteps, startSteps} from "point_of_sale.tour.utils";
import {NumberPopup} from "point_of_sale.tour.NumberPopupTourMethods";
import {PaymentScreen} from "point_of_sale.tour.PaymentScreenTourMethods";
import {ProductScreen} from "point_of_sale.tour.ProductScreenTourMethods";
import {ReceiptScreen} from "pos_loyalty_redeem_payment.tour.ReceiptScreenTourMethods";
import {TextInputPopup} from "point_of_sale.tour.TextInputPopupTourMethods";
import {TicketScreen} from "point_of_sale.tour.TicketScreenTourMethods";
import Tour from "web_tour.tour";

startSteps();
ProductScreen.do.confirmOpeningPopup();
ProductScreen.do.clickHomeCategory();

ProductScreen.exec.addOrderline("Letter Tray", "1");
ProductScreen.check.selectedOrderlineHas("Letter Tray", "1.0");
ProductScreen.do.clickPayButton();
PaymentScreen.check.isShown();
PaymentScreen.do.clickPaymentMethod("Voucher");
TextInputPopup.check.isShown();
TextInputPopup.do.inputText("044123456");
TextInputPopup.do.clickConfirm();
NumberPopup.check.isShown();
NumberPopup.do.pressNumpad("1");
NumberPopup.do.clickConfirm();
PaymentScreen.check.selectedPaymentlineHas("Voucher", "1.00");
PaymentScreen.do.clickPaymentMethod("Cash");
PaymentScreen.check.validateButtonIsHighlighted(true);
PaymentScreen.do.clickValidate();
ReceiptScreen.check.totalAmountContains("5.28");
ReceiptScreen.check.couponCodeIsShown("044123456");
ReceiptScreen.do.clickNextOrder();

// Check that code is shown from refund orders button.
ProductScreen.do.clickRefund();
TicketScreen.do.selectOrder("-0001");
TicketScreen.do.clickControlButton("Print Receipt");
ReceiptScreen.check.isShown();
ReceiptScreen.check.couponCodeIsShown("044123456");

Tour.register(
    "CouponCodeInRedeemPaymentReceipt",
    {test: true, url: "/pos/web"},
    getSteps()
);
