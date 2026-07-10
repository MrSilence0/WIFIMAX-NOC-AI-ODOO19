/** @odoo-module **/

import { registry } from "@web/core/registry";
import { WifimaxHomeMenu } from "./home_menu";

// Registramos el componente como una acción ejecutable por Odoo
registry.category("actions").add("wifimax_home_menu_action", WifimaxHomeMenu);