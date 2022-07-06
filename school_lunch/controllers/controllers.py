# -*- coding: utf-8 -*-

from odoo import http
import datetime
from odoo.http import request
import time
from dateutil.relativedelta import relativedelta
import pprint

FMT = '%A, %d %b %Y'

class SchoolLunch(http.Controller):
    @http.route(['/menu', '/menu/<int:date>'], auth='public', type='http', website=True)
    def menu(self, date=None, **kw):
        dt = datetime.datetime.fromtimestamp(date or time.time())
        return http.request.render('school_lunch.menu', {
            'date': dt,
            'timestamp': date,
            'dmonth': relativedelta(months=1),
            'kids': request.env['school_lunch.kid'].browse(request.session.get('mykids', [])),
        })

    @http.route(['/school/kids'], auth='public', type='http', website=True)
    def school_kids(self, date=None, **kw):
        classes = request.env['school_lunch.class_name'].search([])
        kids = request.env['school_lunch.kid'].search([])
        my_kids = request.env['school_lunch.kid'].browse(request.session.get('mykids', []))
        return http.request.render('school_lunch.kids', {
            'classes': classes,
            'kids': kids,
            'my_kids': my_kids,
        })

    @http.route(['/school/kid/add'], auth='public', type='http', website=True, methods=["POST"])
    def school_kid_add(self, kid_id=None, **kw):
        if not kid_id:
            return request.redirect('/school/kids')
        kid_id = int(kid_id)
        d = request.session.get('mykids', [])
        if kid_id not in d:
            d.append(int(kid_id))
        request.session['mykids'] = d
        return request.redirect('/school/kids')

    @http.route(['/school/kid/remove/<int:kid_id>'], auth='public', type='http', website=True)
    def school_kid_remove(self, kid_id, **kw):
        d = request.session.get('mykids', [])
        d.remove(int(kid_id))
        request.session['mykids'] = d
        return request.redirect('/school/kids')

    @http.route(['/school/order_set'], type="json", auth="public", website=True, methods=["POST"])
    def school_order_set(self, orders, **kwargs):
        if not orders:
            return False
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)
        sale_order.order_line = sale_order.order_line.filtered(lambda line: not line.lunch_ids)

        menus = request.env['school_lunch.menu'].browse(map(int, orders.keys()))
        meals = {}            # {meal_type: [(menu_id, kid_id)] }
        for menu in menus:
            for kid in orders[str(menu.id)]:
                meals.setdefault(menu.meal_type, [])
                meals[menu.meal_type].append((menu.id, kid))

        for meal_type, orders in meals.items():
            product_id = request.env.ref('school_lunch.product_'+meal_type).sudo()
            so = sale_order.sudo()
            line_id = so._cart_update(
                product_id=product_id.id,
                set_qty=len(orders)
            )['line_id']
            for order in orders:
                request.env['school_lunch.order'].sudo().create({
                    'sale_line_id': line_id,
                    'menu_id': order[0],
                    'kid_id': order[1]
                })

        return True

    @http.route(['/school/order_prepare'], type="json", auth="public", website=True, methods=["POST"])
    def school_order_prepare(self, date=None, **kwargs):
        max_day = int(request.env["ir.config_parameter"].sudo().get_param("school_lunch.lunch_block") or 26)
        alert_day = int(request.env["ir.config_parameter"].sudo().get_param("school_lunch.lunch_reminder") or 20)
        now = datetime.datetime.now()
        max_date = now + relativedelta(months = (now.day <= max_day) and 1 or 2, day=1)

        date = datetime.datetime.fromtimestamp(date and int(date) or max_date.timestamp())
        dt_from = date + relativedelta(day=1)
        dt_to = date + relativedelta(day=1, months=1) - datetime.timedelta(days=1)
        kids = request.env['school_lunch.kid'].browse(request.session.get('mykids', []))
        kid_ids = kids.ids

        menus = request.env['school_lunch.menu'].search([('date','>=', dt_from.strftime('%Y-%m-%d')), ('date', "<=", dt_to.strftime('%Y-%m-%d'))])
        allergy_ids = set([al.id for m in menus for al in m.allergy_ids])
        allergies = request.env['school_lunch.allergy'].search([('id', 'in', list(allergy_ids))])

        unblock = False
        for kid in kids:
            if kid.unblock_date and kid.unblock_date >= datetime.date.today():
                unblock = True
        result = {
            'kids': [{'id': kid.id, 'shortname': kid.shortname} for kid in kids],
            'allergies': [{'id': al.id, 'name': al.name} for al in allergies],
            'readonly': (date<=max_date) and not unblock,
            'dt_block': max_day,
            'dt_alert': alert_day,
            'menus': []
        }
        for menu in menus:
            if (not len(result['menus'])) or (result['menus'][-1]['date'] != menu.date.strftime(FMT)):
                result['menus'].append({
                    'date': menu.date.strftime(FMT),
                    'day_of_week': menu.date.weekday()+1,
                    'meals': []
                })
            menu = menu.sudo()
            orders = menu.order_ids.filtered(lambda order: order.kid_id.id in kid_ids)
            menu_kids = orders.filtered(lambda order: order.state=='draft').mapped('kid_id.id')
            ordered_kids = orders.filtered(lambda order: order.state=='confirmed').mapped('kid_id.id')
            result['menus'][-1]['meals'].append({
                'id': menu.id,
                'meal_type': menu.meal_type,
                'state': 'active',
                'name': menu.name,
                'allergies': [{'id': a.id, 'name': a.name} for a in menu.allergy_ids],
                'kids': menu_kids,
                'kids_ordered': ordered_kids
            } )
        return result

    @http.route(['/school/classes_get'], type="json", auth="public", website=True, methods=["POST"])
    def school_classes_get(self, class_id=None, **kwargs):
        classes = request.env['school_lunch.class_name'].search([])
        if not class_id:
            class_id = classes[0].id
        kids = request.env['school_lunch.kid'].search([('class_id','=',int(class_id))])
        result = {
            'classes': [{'id': c.id, 'name': c.name} for c in classes],
            'kids': [{'id': k.id, 'shortname': k.shortname} for k in kids]
        }
        return result
