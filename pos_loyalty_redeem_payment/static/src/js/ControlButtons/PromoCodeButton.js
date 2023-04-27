/** @odoo-module **/
/** © 2023 - FactorLibre - Juan Carlos Bonilla <juancarlos.bonilla@factorlibre.com>
    License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html). **/

import {PromoCodeButton} from "@pos_loyalty/js/ControlButtons/PromoCodeButton";
import Registries from "point_of_sale.Registries";

export const PromoCodeButtonInherit = (OriginalPromoCodeButton) =>
    class extends OriginalPromoCodeButton {
        async onClick() {
            if (this.env.pos.get_order().get_orderlines().length) {
                super.onClick();
            }
        }
    };

Registries.Component.extend(PromoCodeButton, PromoCodeButtonInherit);
