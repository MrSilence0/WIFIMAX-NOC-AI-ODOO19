/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class WifimaxHomeMenu extends Component {
    static template = "wifimax_noc_ai.HomeMenu";

    setup() {
        this.menuService = useService("menu");
    }

    // Obtiene las apps con permisos para el usuario actual
    get apps() {
        return this.menuService.getApps();
    }

    // Acción al hacer clic sobre un icono del tablero
    async onAppClick(app) {
        await this.menuService.selectMenu(app);
    }
}