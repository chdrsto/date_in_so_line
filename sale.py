# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2015 Dragan Stojkovic
# All Right Reserved
#
# Author : Dragan Stojkovic
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from openerp.osv import osv, fields
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons import decimal_precision as dp
from openerp import netsvc
from openerp.tools.translate import _

class sale_order(osv.osv):
    _inherit = "sale.order"
    _columns = {
        'soplanned_date':fields.date('SO Planned Delivery date',
                                     readonly=True,
                                     states={'draft':[('readonly',False)],'sent':[('readonly',False)]},
                                     help="Fullfill to force 'Planned delivery Date' in all lines "
                                          "according to the selected date (when creating the SO lines).\n"
                                          "Leave empty to let the system compute lines values.\n"
                                          "You can use the button 'Update line planned date' afterwards "
                                          "to force the value once it has been computed.")
    }

    # Calculation of the Delivery Dates
    def get_delivery_date(self, cr, uid, order, line, start_date, context=None):
        # If there is a customer requested delivery date on SO line item, than take this date else compute the delivery date according to the Odoo default setup with lead times
        if line.planned_date:
            delivery_date = datetime.strptime(line.planned_date, DEFAULT_SERVER_DATE_FORMAT)
        else:
            delivery_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=line.delay or 0.0)
        # Calculate the delivery date according to the customer requested delivery date and system default lead times for delivery
        delivery_date = (delivery_date - timedelta(days=order.company_id.security_lead)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return delivery_date

    # This function sets all Sales Order line item to the Customer requested delivery date from the Sales Order Header field (soplanned_date)
    def set_delivery_dates(self, cr, uid, ids, context={}):
        if not ids :
            return False
        
        if not self.browse(cr, uid, ids[0]).soplanned_date :
            raise osv.except_osv(_('Error !'),
                                 _("Please fill a valid Customer requested delivery date "
                                   "before using this function"))

        for salesorder in self.browse(cr, uid, ids, context):
            # This function iterates through the Sales Order Line items and adjusts them according to the SO Header date
            for line in salesorder.order_line :
                line.write({'planned_date': self.browse(cr, uid, ids[0]).soplanned_date}, context=context)
        return True

    # This function iterates through the Sales Order Line items and groups them in one or multiple delivery orders
    def action_ship_create(self, cr, uid, ids, context=None):
        picking_pool = self.pool.get('stock.picking')
        if not ids:
            return False

        for order in self.browse(cr, uid, ids, context=context):
            lines_by_group = {}
            for line in order.order_line:
                if line.planned_date:
                    if not lines_by_group.get(line.planned_date, False):
                        lines_by_group[line.planned_date] = []
                    lines_by_group[line.planned_date].append(line)
                else:
                    if not lines_by_group.get(0, False):
                        lines_by_group[0].append(line)

            # It creates groups of line items which have to be delivered in a batch .. according to the customer requested delivery date
            for group in lines_by_group:
                if not group:
                    # If there is no group, the system will call function to create a new delivery order
                    self.create_deliveryorder(cr, uid, order, lines_by_group[group], None, context=context)
                else:
                    # If there is already a group available for this batch, the system will call function to assign the line item to the delivery order batch
                    picking_vals = super(sale_order, self)._prepare_order_picking(cr, uid, order, context=context)
                    picking_id = picking_pool.create(cr, uid, picking_vals, context=context)
                    self.create_deliveryorder(cr, uid, order, lines_by_group[group], picking_id, context=context)
        return True
    # This function created one or multiple delivery orders according to the customer requested delivery dates
    def create_deliveryorder(self, cr, uid, order, order_lines, picking_id=False, context=None):
        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')
        procurement_obj = self.pool.get('procurement.order')
        proc_ids = []

        for line in order_lines:
            if line.state == 'done':
                continue

            delivery_date = self.get_delivery_date(cr, uid, order, line, order.date_order, context=context)

            if line.product_id:
                if line.product_id.product_tmpl_id.type in ('product', 'consu'):
                    if not picking_id:
                        picking_id = picking_obj.create(cr, uid, self._prepare_order_picking(cr, uid, order, context=context))
                    move_id = move_obj.create(cr, uid, self._prepare_order_line_move(cr, uid, order, line, picking_id, delivery_date, context=context))
                else:
                    move_id = False

                proc_id = procurement_obj.create(cr, uid, self._prepare_order_line_procurement(cr, uid, order, line, move_id, delivery_date, context=context))
                proc_ids.append(proc_id)
                line.write({'procurement_id': proc_id})
                self.ship_recreate(cr, uid, order, line, move_id, proc_id)

        wf_service = netsvc.LocalService("workflow")
        if picking_id:
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)

        for proc_id in proc_ids:
            wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)

        val = {}
        if order.state == 'shipping_except':
            val['state'] = 'progress'
            val['shipped'] = False

            if (order.order_policy == 'manual'):
                for line in order.order_line:
                    if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                        val['state'] = 'manual'
                        break
        order.write(val)
        return True

class sale_order_line(osv.osv):
    
    _inherit = "sale.order.line"

    def get_default_delivery_date(self, cr, uid, context={}) :
        #return context.get('myplanned_date', False)
        sales = self.pool.get('sale_order')
        vSOplanned_date = super(sales, self).get_delivery_date(cr, uid, sales, context=context)
        return (vSOplanned_date)
        

    def get_delivered_qty(self, cr, uid, ids, field_name, arg, context=None):
        #move_obj = self.pool.get('stock.move')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            qty = 0
            
            for move in line.move_ids:
                if move.state == 'done':
                    qty += move.product_qty
                    
            res[line.id] = qty
        return res
    
    def get_product_onstock(self, cr, uid, ids, field_names=None, arg=False, context=None):

        if context is None:
            context = {}
        res = {}
        
        for line in self.browse(cr,uid,ids,context):
            res[line.id] = {'qty_available': line.product_id and line.product_id.qty_available,
                            'virtual_available': line.product_id and line.product_id.virtual_available}
        return res

    _columns = {
                'planned_date':fields.date('Planned Delivery date',
                                           states={'draft':[('readonly',False)]},
                                           help="Put the planned delivery date for this lines. "
                                           "This will compute for you the delay to put on the line.",),
                'delivered_qty':fields.function(get_delivered_qty, digits_compute=dp.get_precision('Product UoM'), string='Delivered Qty'),
                'qty_available':fields.function(get_product_onstock, multi='qty_available',
                                                type='float',  digits_compute=dp.get_precision('Product UoM'),
                                                string='Quantity On Hand'),
                'virtual_available': fields.function(get_product_onstock, multi='qty_available',
                                                     type='float',  digits_compute=dp.get_precision('Product UoM'),
                                                     string='Quantity Available')
                }
    _defaults = {'planned_date': get_default_delivery_date, 'sequence': 10, }

