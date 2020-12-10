# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import api, fields, models
from datetime import datetime, date

from odoo.exceptions import Warning

def urlplus(url, params):
    return werkzeug.Href(url)(params or None)

class ProductRealEstate(models.Model):
    _inherit = 'product.template'

    is_real_estate_product = fields.Boolean(string='Real Estate Product')
    product_property_type_id = fields.Many2one('real.estate.type', 'Property Type')
    property_location_id = fields.Many2one('property.location','Property Location')
    
    document_attach_ids = fields.One2many('ir.attachment', string='Attached Documents', compute='website_document_compute')

    def website_document_compute(self):

        for product in self:
            
            products = self.env['ir.attachment'].search([('res_model', '=', 'product.template'),('res_id', '=', product.id),('store_fname', '!=', False)], order='mimetype')
            product.document_attach_ids = products

    def site_google_map_link(self, zoom=10):
        params = {
            'q': '%s %s,%s,%s,%s' % (self.property_location_id.addr1 or '',self.property_location_id.addr2 or '',self.property_location_id.addr_city or '', self.property_location_id.addr_state.name or '', self.property_location_id.addr_country.name or ''),
            'z': zoom,
        }
        return urlplus('https://maps.google.com/maps', params)

class SalesCommissionSettings(models.Model):
    _inherit = 'sale.order'
    
    installments_ids = fields.One2many('account.move','rel_sale_order','Installments')
    installments_is = fields.Boolean('Installments', default=False)
    
    def action_view_invoice1(self):
        action = self.env.ref('account.action_move_out_invoice_type')
        result = action.read()[0]
        result.pop('id', None)
        result['context'] = {}
        result['domain'] = [('rel_sale_order', '=', self.id),('type','=','out_invoice')]
        tree_view_id = self.env.ref('account.view_invoice_tree', False)
        form_view_id = self.env.ref('account.view_invoice_form', False)
        result['views'] = [(tree_view_id and tree_view_id.id or False, 'tree'),(form_view_id and form_view_id.id or False, 'form')]
        return result
    
    def create_installments(self):
        self.write({'installments_is':True})
        invoice_object = self.env['account.move']
        invoice_line_obj = self.env['account.move.line']
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        
        for pr in self.order_line:
            for i in range(1, pr.product_id.no_of_installments+1):               
                
                tax_ids = []
                for tax in pr.tax_id:
                    tax_ids.append(tax.id)
                
                order_id = invoice_object.create({
                    'invoice_origin': self.name,
                    'partner_id': self.partner_id.id, 
                    'rel_sale_order': self.id, 
                    'type': 'out_invoice',
                    'journal_id': journal.id,
                    'invoice_line_ids':[(0,0,{
                        'product_id': pr.product_id.id,
                        'name':pr.product_id.name,
                        'quantity': pr.product_uom_qty,
                        'discount': pr.discount,
                        'price_unit': self.amount_total/pr.product_id.no_of_installments,
                        'tax_ids': [(6,0,tax_ids)],
                        })],
                    })


class PropertyType(models.Model):
    _name = 'real.estate.type'
    _rec_name = 'property_name'
    
    property_name = fields.Char('Name')
    property_code = fields.Char('Code')


class PropertyLocation(models.Model):
    _name = 'property.location'
    _rec_name = 'addr_city'
    
    addr1 = fields.Char('Address Line1')
    addr2 = fields.Char('Address Line2')
    addr_city = fields.Char('City')
    addr_state = fields.Many2one('res.country.state', 'State')
    addr_country = fields.Many2one('res.country', 'Country')


class ProductProductProperty(models.Model):
    
    _inherit = 'product.product'
    
    no_of_installments = fields.Integer('No of Installments')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
