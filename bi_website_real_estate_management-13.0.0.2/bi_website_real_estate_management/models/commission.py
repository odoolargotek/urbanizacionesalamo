# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class SalesCommission(models.Model):

    _name = 'sale.commission.sheet'
    _order = "id desc"
    
    @api.onchange('start_date')
    def calc_commission_end_date(self):
        date_1 = (datetime.strptime(self.start_date, '%Y-%m-%d')+relativedelta(months =+ 1))
        self.update({'end_date':date_1})
    
    def calc_total_sheet_amt(self):
        total = 0.0
        for am in self.commission_line_ids:
            total += am.amount
        self.update({'total_commission_amt': total})
    
    name = fields.Char('Name', default='New')
    sales_partner = fields.Many2one('res.partner', 'Sales Partner')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date', readonly='1')
    commission_product_id = fields.Many2one('product.product', 'Commission Product')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    total_commission_amt = fields.Float('Total Commission Amount', compute='calc_total_sheet_amt')
    commission_paid = fields.Boolean('Commission Paid')
    commission_line_ids = fields.One2many('sale.commission.line', 'commission_id', 'Commission Lines')
    
    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('sale.commission.sheet') or _('New')
        res = super(SalesCommission, self).create(vals)
        return res
    
    
class SalesCommissionLines(models.Model):
    
    _name = 'sale.commission.line'
    _rec_name = 'sales_partner'
    _order = "id desc"
    
    commission_date = fields.Date('Commission Date')
    sales_partner = fields.Many2one('res.partner', 'Sales Partner')
    source = fields.Char('Source Document')
    amount = fields.Float('Amount')
    state = fields.Selection([('draft','Draft'),('paid','Paid')], default='draft', string='Commission Line Paid')
    commission_id = fields.Many2one('sale.commission.sheet', 'Commission Sheet')
    
    
class CreateCommissionSalesOrder(models.Model):
    _inherit = 'sale.order'
    
    def action_confirm(self):
        self._action_confirm()
        if self.env['ir.config_parameter'].sudo().get_param('sale.auto_done_setting'):
            self.action_done()
        
        #################################################################################################################################
        
        if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_configuration == 'sale_order':
            commission_line_obj = self.env['sale.commission.line']
            commission_calc_amt = self.env['commission.settings']
            comm_calc_product = self.env['product.template']
            comm_worksheet_obj = self.env['sale.commission.sheet']
            
            order_product = []
            for i in self.order_line:
                order_product = i.product_id.product_tmpl_id
            
            order_product_category = []
            for j in self.order_line:
                order_product_category = j.product_id.product_tmpl_id.categ_id
            
            commission_product = self.env['product.product'].search([('product_tmpl_id.is_commission_product','=', True)])
            
            date_1 = (datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')+relativedelta(months =+ 1))
            
            if order_product.is_real_estate_product == True:
                sheet = comm_worksheet_obj.create({'sales_partner': self.partner_id.id, 'commission_product_id': commission_product[0].id, 'start_date': datetime.now().date(), 'end_date':date_1.date()})
            
            
            for co in self.product_comm_level_ids:
                
                # Commission Calculation based on sales team
                if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_calc_on == 'sales_team':
                    if co.user_partner_id:
                        if order_product.is_real_estate_product == True:
                            comm_filter = commission_calc_amt.search([('sales_team_id','=', self.team_id.id),('commission_level_id','=', co.commission_level_id.id)])
                            commission_line_obj.create({'sales_partner': co.user_partner_id.id, 'commission_date': datetime.now().date(), 'source': self.name, 'amount': (comm_filter_p.percentage * self.amount_total)/100, 'commission_id': sheet.id})
                
                #  Commission Calculation based on product
                if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_calc_on == 'product':
                    if co.user_partner_id:
                        if order_product.is_real_estate_product == True:
                            comm_filter_p = commission_calc_amt.search([('product_id','=', order_product.id),('commission_level_id','=', co.commission_level_id.id)])
                            commission_line_obj.create({'sales_partner': co.user_partner_id.id, 'commission_date': datetime.now().date(), 'source': self.name, 'amount': (comm_filter_p.percentage * self.amount_total)/100, 'commission_id': sheet.id})
                
                #  Commission Calculation based on product category
                if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_calc_on == 'product_category':
                    if co.user_partner_id:
                        if order_product.is_real_estate_product == True:
                            comm_filter_p_c = commission_calc_amt.search([('product_category_id','=', order_product_category.id),('commission_level_id','=', co.commission_level_id.id)])
                            commission_line_obj.create({'sales_partner': co.user_partner_id.id, 'commission_date': datetime.now().date(), 'source': self.name, 'amount': (comm_filter_p.percentage * self.amount_total)/100, 'commission_id': sheet.id})
        
        #################################################################################################################################
        return True
        

class CreateCommissionInvoice(models.Model):
    
    _inherit = 'account.move' 
    
    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft']):
            raise UserError(_("Invoice must be in draft or Pro-forma state in order to validate it."))
        to_open_invoices.action_date_assign()
        to_open_invoices.action_move_create()
        
        ###################################### Commission calculation on Invoice ###################################################
        
        if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_configuration == 'invoice':
            commission_line_obj = self.env['sale.commission.line']
            commission_calc_amt = self.env['commission.settings']
            comm_calc_product = self.env['product.template']
            comm_worksheet_obj = self.env['sale.commission.sheet']
            
            commission_product = self.env['product.product'].search([('product_tmpl_id.is_commission_product','=', True)])
            date_1 = (datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')+relativedelta(months =+ 1))
                
            inv_product = []
            for i in self.invoice_line_ids:
                inv_product = i.product_id.product_tmpl_id
                
            inv_product_category = []
            for j in self.invoice_line_ids:
                inv_product_category = j.product_id.product_tmpl_id.categ_id
                
                
            if inv_product.is_real_estate_product == True:
                sheet = comm_worksheet_obj.create({'sales_partner': self.partner_id.id, 'commission_product_id': commission_product[0].id, 'start_date': datetime.now().date(), 'end_date':date_1.date()})
                
                
            for co in self.product_comm_level_ids:
                
                # Commission Calculation based on sales team
                if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_calc_on == 'sales_team':
                    if co.user_partner_id:
                        if inv_product.is_real_estate_product == True:
                            comm_filter = commission_calc_amt.search([('sales_team_id','=', self.rel_sale_order.team_id.id),('commission_level_id','=', co.commission_level_id.id)])
                            commission_line_obj.create({'sales_partner': co.user_partner_id.id, 'commission_date': datetime.now().date(), 'source': self.number, 'amount': comm_filter.percentage, 'commission_id': sheet.id})
                
                #  Commission Calculation based on product
                if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_calc_on == 'product':
                    if co.user_partner_id:
                        if inv_product.is_real_estate_product == True:
                            comm_filter_p = commission_calc_amt.search([('product_id','=', inv_product.id),('commission_level_id','=', co.commission_level_id.id)])
                            commission_line_obj.create({'sales_partner': co.user_partner_id.id, 'commission_date': datetime.now().date(), 'source': self.number, 'amount': comm_filter_p.percentage, 'commission_id': sheet.id})
                
                #  Commission Calculation based on product category
                if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_calc_on == 'product_category':
                    if co.user_partner_id:
                        if inv_product.is_real_estate_product == True:
                            comm_filter_p_c = commission_calc_amt.search([('product_category_id','=', inv_product_category.id),('commission_level_id','=', co.commission_level_id.id)])
                            commission_line_obj.create({'sales_partner': co.user_partner_id.id, 'commission_date': datetime.now().date(), 'source': self.number, 'amount': comm_filter_p_c.percentage, 'commission_id': sheet.id})

    
        #########################################################################################
        
        return to_open_invoices.invoice_validate()       
        

class CreateCommissionPayment(models.Model):
    _inherit = 'account.payment'  
    
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            if rec.payment_type == 'transfer':
                sequence_code = 'account.payment.transfer'
            else:
                if rec.partner_type == 'customer':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.customer.invoice'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.customer.refund'
                if rec.partner_type == 'supplier':
                    if rec.payment_type == 'inbound':
                        sequence_code = 'account.payment.supplier.refund'
                    if rec.payment_type == 'outbound':
                        sequence_code = 'account.payment.supplier.invoice'
            rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
            if not rec.name and rec.payment_type != 'transfer':
                raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)

            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()
            
            ############################################### Commission calculation on Invoice ########################################################
            
            if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_configuration == 'payment':
                commission_line_obj = self.env['sale.commission.line']
                commission_calc_amt = self.env['commission.settings']
                comm_calc_product = self.env['product.template']
                comm_worksheet_obj = self.env['sale.commission.sheet']
                
                commission_product = self.env['product.product'].search([('product_tmpl_id.is_commission_product','=', True)])
                date_1 = (datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')+relativedelta(months =+ 1))
                    
                pay_product = []
                for i in self.invoice_ids:
                    for j in i.invoice_line_ids:
                        pay_product = j.product_id.product_tmpl_id
                    
                pay_product_category = []
                for m in self.invoice_ids:
                    for n in m.invoice_line_ids:
                        pay_product_category = n.product_id.product_tmpl_id.categ_id
                    
                    
                if pay_product.is_real_estate_product == True:
                    sheet = comm_worksheet_obj.create({'sales_partner': self.partner_id.id, 'commission_product_id': commission_product[0].id, 'start_date': datetime.now().date(), 'end_date':date_1.date()})
                    
                    
                for co in self.product_comm_level_ids:
                    
                    #  Commission Calculation based on product
                    if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_calc_on == 'product':
                        if co.user_partner_id:
                            if pay_product.is_real_estate_product == True:
                                comm_filter_p = commission_calc_amt.search([('product_id','=', pay_product.id),('commission_level_id','=', co.commission_level_id.id)])
                                commission_line_obj.create({'sales_partner': co.user_partner_id.id, 'commission_date': datetime.now().date(), 'source': self.name, 'amount': comm_filter_p.percentage, 'commission_id': sheet.id})
                    
                    #  Commission Calculation based on product category
                    if self.env['res.config.settings'].search([], limit=1, order="id desc").commission_calc_on == 'product_category':
                        if co.user_partner_id:
                            if pay_product.is_real_estate_product == True:
                                comm_filter_p_c = commission_calc_amt.search([('product_category_id','=', pay_product_category.id),('commission_level_id','=', co.commission_level_id.id)])
                                commission_line_obj.create({'sales_partner': co.user_partner_id.id, 'commission_date': datetime.now().date(), 'source': self.name, 'amount': comm_filter_p_c.percentage, 'commission_id': sheet.id})

            #######################################################################################################

            rec.write({'state': 'posted', 'move_name': move.name})      
             
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
