/** @odoo-module **/
/** © 2023 - FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). **/

import {Order, Payment} from "point_of_sale.models";
import Registries from "point_of_sale.Registries";

export const RedeemPaymentOrder = (OriginalOrder) =>
    class extends OriginalOrder {
        has_redeemption_code() {
            return this.paymentlines.some((line) => line.payment_method.redeem_code);
        }
        is_paid_with_coupon() {
            let res = super.is_paid_with_coupon();
            if (!res)
                res = this.paymentlines.some((pl) => pl.payment_method.redeem_code);
            return res;
        }

        has_redeem_lines() {
            return this.paymentlines.some((pl) => pl.payment_method.redeem_code);
        }

        wait_for_push_order() {
            let result = super.wait_for_push_order(...arguments);
            result = Boolean(result || this.has_redeem_lines());
            return result;
        }
    };

Registries.Model.extend(Order, RedeemPaymentOrder);

export const PosVoucherRedeemPayment = (OriginalPayment) =>
    class extends OriginalPayment {
        constructor(obj, options) {
            super(obj, options);
            this.coupon_data = this.coupon_data || null;
        }

        export_as_JSON() {
            const json = super.export_as_JSON(...arguments);
            json.coupon_data = this.coupon_data;
            return json;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.coupon_data = json.coupon_data;
        }

        export_for_printing() {
            const result = super.export_for_printing();
            result.coupon_data = this.coupon_data;
            result.code = this.coupon_data ? this.coupon_data.code.trim() : result.code;

            return result;
        }
    };

Registries.Model.extend(Payment, PosVoucherRedeemPayment);
