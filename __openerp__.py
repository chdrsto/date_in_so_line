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

{
    "name": "Date in SO lines",
    "description": """
            This module allows you to set a planned shipment date into a Sale order.
            When the SO is confirmed the Delivery Order is automtically computed this way
            you do not have to use day for computing Delivery date of generated picking.
            If a date is set on the SO, it will automatically be taken in so line, 
            if not it will recompute a date based on the lead time. 
            If the Sales Order has different delivery dates, the module  will generate
            the necessary delivery orders according tho the delivery dates.
            This means, if there are multiple delivery dates, the module will create multiple
            Delivery orders and set the delivery date according the the Sales Order Line date. 
            """,
    "version": "7.0",
    'category': 'Generic Modules/Sales & Purchases',
    "depends": [
                    "base",
                    "sale",
                    "warning",
                ],
    "author": "Dragan Stojkovic",
    "init_xml": [],
    "update_xml": [
                        "sale_order_line_view.xml",
                   ],
    "installable": True,
    "active": False,
}
