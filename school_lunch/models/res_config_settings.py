# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, date
from dateutil.relativedelta import relativedelta

from odoo import api, exceptions, fields, models, _


class resCompany(models.Model):
    _inherit = 'res.company'

    lunch_reminder_template_id = fields.Many2one('mail.template', string="Lunch Reminder Email")
    lunch_signin = fields.Boolean("Force Sign In", help="Force users to sign in to add children in their session", default=True)

    def _cron_school_lunch_reminder(self):
        menu = self.env['school_lunch.menu']
        if not menu.search_count([('date', ">=", date.today() + relativedelta(months=1, day=1)), ('date', "<", date.today() + relativedelta(months=2, day=1))]):
            return False
        return self.env['res.partner'].search([('kid_ids', '!=', False), ('email','ilike','%')])._school_lunch_mail()

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lunch_block = fields.Integer(string="Deadline to Order", config_parameter='school_lunch.lunch_block', default=26, help="Day of the month to order for next month. 0 for no deadline")
    lunch_reminder = fields.Integer(string="Lunch Reminder", default=lambda self: self._get_lunch_reminder(), inverse='_set_lunch_reminder')
    lunch_reminder_template_id = fields.Many2one('mail.template',
            related="company_id.lunch_reminder_template_id", string="Email Template", readonly=False,
            default=lambda self: self.env.ref('school_lunch.mail_template_school_lunch'))

    def _get_lunch_reminder(self):
        cron = self.env.ref('school_lunch.school_menu_reminder')
        return cron.active and cron.nextcall.day or 0

    def _set_lunch_reminder(self):
        cron = self.env.ref('school_lunch.school_menu_reminder')
        for setting in self:
            day = setting.lunch_reminder
            cron.active = bool(day)
            if day:
                cron.nextcall = cron.nextcall + relativedelta(day=day)
