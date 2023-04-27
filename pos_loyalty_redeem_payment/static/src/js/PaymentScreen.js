/** @odoo-module **/
/** © 2023 - FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). **/

import NumberBuffer from "point_of_sale.NumberBuffer";
import PaymentScreen from "point_of_sale.PaymentScreen";
import Registries from "point_of_sale.Registries";

export const CouponPosPaymentScreen = (OriginalPaymentScreen) =>
    class extends OriginalPaymentScreen {
        setup() {
            super.setup();
            this.payment_methods_from_config = this.env.pos.payment_methods.filter(
                this.filterPaymentMethods,
                this
            );
        }

        filterPaymentMethods(method) {
            // If order amount is positive, we don't want to show paymentMethods with 'is_voucher' to true.
            // However if paymentMethod allows to redeem amount, we should display it.
            if (this.currentOrder.get_total_with_tax() > 0) {
                return (
                    this.env.pos.config.payment_method_ids.includes(method.id) &&
                    (!method.is_voucher || method.redeem_code)
                );
            }
            return this.env.pos.config.payment_method_ids.includes(method.id);
        }

        _updateSelectedPaymentline() {
            if (this.selectedPaymentLine && this.selectedPaymentLine.coupon_data)
                return;
            super._updateSelectedPaymentline();
        }

        async isValidCode(code, paymentMethod) {
            const order = this.env.pos.get_order();
            const customer = order.get_partner();
            return await this.env.services.rpc({
                model: "pos.config",
                method: "use_coupon_code",
                args: [
                    [this.env.pos.config.id],
                    code,
                    order.creation_date,
                    customer ? customer.id : false,
                ],
                kwargs: {
                    context: {
                        from_payment_screen: true,
                        payment_method_id: paymentMethod.id,
                    },
                },
            });
        }

        // If voucher code has already been activated,
        // we cannot used twice in same or different orders without being processed.
        // First we have to process the order and then use it again.
        codeIsDuplicated(orders, code) {
            return orders.some((order) =>
                order.paymentlines.some(
                    (line) => line.coupon_data && line.coupon_data.code === code
                )
            );
        }

        hasBeenScanned(code) {
            const pending_orders = this.env.pos.get_order_list();
            if (this.codeIsDuplicated(pending_orders, code)) {
                this.showNotification(
                    this.env._t(
                        "That coupon code has already been scanned and activated. Please, process pending orders.",
                        5000
                    )
                );
                return 0;
            }
            return 1;
        }

        getPlaceholder(paymentName) {
            const MAPPER = {
                vale: this.env._t("Voucher"),
                regalo: this.env._t("Gift Card"),
            };
            const result = ["vale", "regalo"].filter((str) =>
                paymentName.includes(str)
            );
            return result ? MAPPER[result[0]] : this.env._t("Voucher or Gift Card");
        }

        async insertAndValidateCode(paymentMethod) {
            const voucher_type = this.getPlaceholder(paymentMethod.name.toLowerCase());
            const {confirmed, payload: code} = await this.showPopup("TextInputPopup", {
                title: this.env._t("Enter Code"),
                startingValue: "",
                placeholder: voucher_type,
            });
            if (!confirmed || !this.hasBeenScanned(code)) return 0;

            const trimmedCode = code.trim();
            if (trimmedCode) {
                const {successful, payload} = await this.isValidCode(
                    trimmedCode,
                    paymentMethod
                );
                if (successful) {
                    return {payload, code};
                }
                this.showNotification(payload.error_message, 5000);
            }
            return 0;
        }

        async insertAmountToRedeem(maxVoucherAmount) {
            const to_paid = Math.min(maxVoucherAmount, this.currentOrder.get_due());
            const {confirmed, payload: amount} = await this.showPopup(
                "ResponsiveNumberPopup",
                {
                    startingValue: 0,
                    title: _.str.sprintf(
                        this.env._t("Set amount to redeem, up to %s"),
                        this.env.pos.format_currency(to_paid)
                    ),
                }
            );
            if (confirmed) {
                const new_amount = parseFloat(amount.replace(",", "."));
                if (new_amount <= maxVoucherAmount) {
                    return new_amount;
                }
                this.showPopup("ErrorPopup", {
                    body: _.str.sprintf(
                        this.env._t(
                            "You tried to redeem %s, but maximum for this gift card in this order is %s"
                        ),
                        this.env.pos.format_currency(new_amount),
                        this.env.pos.format_currency(maxVoucherAmount)
                    ),
                });
            }
            return 0;
        }

        // Only valid for voucher and gift card programs
        async applyProgramAsPaymentMethod(paymentMethod) {
            const {payload, code} = await this.insertAndValidateCode(paymentMethod);
            if (payload) {
                const amount = await this.insertAmountToRedeem(payload.points);
                if (amount) {
                    const newPaymentLine =
                        this.currentOrder.add_paymentline(paymentMethod);
                    newPaymentLine.set_amount(amount);
                    // Amount = amount to redeem
                    newPaymentLine.coupon_data = {coupon: payload, amount, code};
                    newPaymentLine.coupon_id = payload.coupon_id;
                    if (newPaymentLine) {
                        NumberBuffer.reset();
                    } else {
                        this.showPopup("ErrorPopup", {
                            title: this.env._t("Error"),
                            body: this.env._t(
                                "There is already an electronic payment in progress."
                            ),
                        });
                    }
                }
            }
        }

        addNewPaymentLine({detail: paymentMethod}) {
            const order = this.currentOrder;
            if (
                order.get_due() &&
                order.get_subtotal() > 0 &&
                paymentMethod.redeem_code
            ) {
                this.applyProgramAsPaymentMethod(paymentMethod);
                return;
            }
            super.addNewPaymentLine(...arguments);
        }
    };

Registries.Component.extend(PaymentScreen, CouponPosPaymentScreen);
