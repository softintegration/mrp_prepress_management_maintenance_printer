# -*- coding: utf-8 -*- 

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round
import math


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    passes_nbr = fields.Integer(string='Number of passes', compute='_compute_passes_nbr')
    is_printer = fields.Boolean(related='workcenter_id.equipment_id.is_printer')

    @api.depends('product_id', 'workcenter_id')
    def _compute_passes_nbr(self):
        for each in self:
            each.passes_nbr = each._get_passes_nbr(each.workcenter_id)

    def _get_passes_nbr(self, workcenter):
        self.ensure_one()
        if workcenter.equipment_id and workcenter.equipment_id.is_printer:
            if self.product_id.both_sides and workcenter.equipment_id.both_sides:
                not_rounded_passes_nbr = max(
                    self.product_id.front_color_cpt / (workcenter.equipment_id.front_color_cpt or 1),
                    self.product_id.back_color_cpt / (workcenter.equipment_id.back_color_cpt or 1))
            elif self.product_id.both_sides and not workcenter.equipment_id.both_sides:
                not_rounded_passes_nbr = math.ceil(
                    self.product_id.front_color_cpt / (workcenter.equipment_id.color_cpt or 1)) + math.ceil(
                    self.product_id.back_color_cpt / (workcenter.equipment_id.color_cpt or 1))
            else:
                not_rounded_passes_nbr = self.product_id.color_cpt / (workcenter.equipment_id.color_cpt or 1)
            return math.ceil(not_rounded_passes_nbr)
        else:
            return 1

    def _get_duration_expected(self, alternative_workcenter=False, ratio=1):
        self.ensure_one()
        if not self.workcenter_id:
            return self.duration_expected * self.passes_nbr
        if not self.operation_id:
            duration_expected_working = (
                                                    self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / 100.0
            if duration_expected_working < 0:
                duration_expected_working = 0
            return (
                        self.workcenter_id.time_start + self.workcenter_id.time_stop + duration_expected_working * ratio * 100.0 / self.workcenter_id.time_efficiency) * self.passes_nbr
        if self.operation_id.draw_based_duration:
            qty_production = self.production_id.draw_nbr
        else:
            qty_production = self.production_id.product_uom_id._compute_quantity(self.qty_production,
                                                                                 self.production_id.product_id.uom_id)
        cycle_number = float_round(qty_production / self.workcenter_id.capacity, precision_digits=0,
                                   rounding_method='UP')
        if alternative_workcenter:
            # TODO : find a better alternative : the settings of workcenter can change
            # in this case we have not to rely on the Number of passes of the current workorder because we have to calculate duration according to
            # the alternative workcenter
            passes_nbr = self._get_passes_nbr(alternative_workcenter)
            duration_expected_working = (
                                                    self.duration_expected - self.workcenter_id.time_start - self.workcenter_id.time_stop) * self.workcenter_id.time_efficiency / (
                                                    100.0 * cycle_number)
            if duration_expected_working < 0:
                duration_expected_working = 0
            alternative_wc_cycle_nb = float_round(qty_production / alternative_workcenter.capacity, precision_digits=0,
                                                  rounding_method='UP')
            return (
                        alternative_workcenter.time_start + alternative_workcenter.time_stop + alternative_wc_cycle_nb * duration_expected_working * 100.0 / alternative_workcenter.time_efficiency) * passes_nbr
        time_cycle = self.operation_id.time_cycle
        return (
                    self.workcenter_id.time_start + self.workcenter_id.time_stop + cycle_number * time_cycle * 100.0 / self.workcenter_id.time_efficiency) * self.passes_nbr
