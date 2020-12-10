odoo.define('bi_website_real_estate_management.variant', function (require) {
'use strict';


	$(document).ready(function() {
		
		$('#request_quote').on('click',function(){
			var product_id = $('.product_id').val();
			if(product_id){
				$('#request_quote').attr("href","/shop/product/quote/"+parseInt(product_id) );
			}
		});

	});

})