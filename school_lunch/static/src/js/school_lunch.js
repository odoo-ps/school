/** @odoo-module **/


var ajax = require('web.ajax');
var core = require('web.core');

var _t = core._t;

const {Component, Store, mount, QWeb, xml} = owl;
const {useDispatch, useStore, useGetters, useRef, useState} = owl.hooks;
const {Router, RouteComponent} = owl.router;
const {whenReady} = owl.utils;

import env from "web.public_env";


class LunchMenu extends Component {
    toggleMenu() {
        const kid = this.props.kid.id;
        const isset = this.props.menu.kids.includes(kid);
        for (var meal of this.props.meals) {
            var index = meal.kids.indexOf(kid);
            if (index > -1)
                meal.kids.splice(index, 1);
        };
        if (! isset)
            this.props.menu.kids.push(kid);
    };
    static props = ["menu", "kid", "meals"];
}
LunchMenu.template = "school_lunch.lunch_menu"


class LunchLine extends Component {
    static props = ["menu", "kids"];
    static components = { LunchMenu };
}
LunchLine.template = "school_lunch.lunch_line"


class LunchMenuTable extends Component {
    async willStart() {
        const result = await this.env.services.rpc({
            route: `/school/get_orders`,
            params: {date: 0}
        });
        this.kids = result.kids;
        this.allergies = result.allergies;
        for (var menu of result.menus) {
            this.menus.push(menu);
        }
    }

    async setup() {
        this.menus = useState([]);
    };

    mealDisplay(menu, meal) {
        console.log(menu);
        return meal.kids.length;
    }

    unselectAllergy(ev) {
        const allergy = parseInt(ev.srcElement.dataset.allergy);
        for (var menu of this.menus) {
            for (var meal of menu.meals) {
                if (!allergy)
                    meal.kids = [];

                for (var al of meal.allergies) {
                    if (al.id == allergy)
                        meal.kids = [];
                }
            }
        }
    }

    async selectMeal(ev) {
        const meal_type = ev.srcElement.dataset.meal;
        const meal_day = parseInt(ev.srcElement.dataset.day);

        for (var menu of this.menus) {
            if (meal_day && meal_day != menu.day_of_week)
                continue;
            for (var meal of menu.meals) {
                meal.kids.length = 0;
                if (meal.meal_type == meal_type) {
                    for (var kid of this.kids) {
                        meal.kids.push(kid.id);
                    }
                }
            }
        }
    };
    static components = { LunchLine }
}
LunchMenuTable.template = "school_lunch.lunch_table"


async function makeEnvironment() {
    const services = Component.env.services;
    const qweb = new QWeb({translateFn: _t});
    const templates = await owl.utils.loadFile('/school_lunch/static/src/xml/lunch_menu.xml?uniq=' + Math.random());
    qweb.addTemplates(templates);
    return Object.assign(env, {qweb, services});
}

async function setup() {
    const env = await makeEnvironment();
    mount(LunchMenuTable, {target: document.getElementById('LunchMenu'), env});
}

whenReady(setup);
