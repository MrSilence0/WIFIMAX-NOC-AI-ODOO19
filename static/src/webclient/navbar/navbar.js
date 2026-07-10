/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { useService } from "@web/core/utils/hooks";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);

        this.action = useService("action");
    },

    async openWifimaxMenu(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        await this.action.doAction(
            "wifimax_noc_ai.action_wifimax_home_menu",
            {
                clearBreadcrumbs: true,
            }
        );
    },
});