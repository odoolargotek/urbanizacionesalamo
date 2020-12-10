# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo import http
from odoo.http import request

class OdooWebsiteProductQuote(http.Controller):
	    	
    @http.route(['/shop/product/quote/<model("product.product"):product_id>'], type='http', auth="public", website=True)
    def get_quote(self, product_id, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        
        values = {
                'product_id' : product_id,
        }
        return request.render("bi_website_real_estate_management.get_quotation_request",values)

    @http.route(['/shop/product/quote/confirm/'], type='http', auth="public", website=True)
    def quote_confirm(self, **post):
        if post.get('debug'):
            return request.render("bi_website_real_estate_management.quote_thankyou")
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry

        product_id = post['product_id']
        
        product_obj = request.env['product.template']        
        partner_obj = request.env['res.partner']
        sale_order_obj = request.env['sale.order']
        sale_order_line_obj = request.env['sale.order.line']
        product_commission_level_obj = request.env['product.commission.level']
        
        customer_obj = request.env['res.partner'].sudo().search([('name','=', post['name'])])
        if not customer_obj:
            partner_obj.sudo().create({ 
              'name' : post['name'],
              'email' : post['email'],
              'phone' : post['phone'],
            })
        
        customer = []
        customer_warranty_obj = request.env['res.partner'].sudo().search([('name','=', post['name'])])
        for cust in customer_warranty_obj:
            customer = cust.id
        
        product_product_obj = request.env['product.product'].browse(int(product_id))
        
        pricelist_id = request.website.get_current_pricelist().id
        
        
        vals = {'partner_id': customer, 'pricelist_id': pricelist_id }  
          
            
        sale_order_create = sale_order_obj.sudo().create(vals)
        
        for comm in customer_warranty_obj.commission_ids: 
            product_commission_level_obj.create({'commission_level_id': comm.commission_level_id.id, 'sale_order_id': sale_order_create.id})
        
        sale_order_line_create = sale_order_line_obj.sudo().create({ 'product_id': product_product_obj[0].id, 'name': product_product_obj.name, 'product_uom_qty': post['quantity'], 'customer_lead':7, 'product_uom':product_product_obj.uom_id.id, 'order_id': sale_order_create.id })  

                                
        return request.render("bi_website_real_estate_management.quote_thankyou")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
