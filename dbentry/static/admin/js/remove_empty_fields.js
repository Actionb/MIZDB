django.jQuery(document).ready(function($){
  
  // Remove empty fields from GET forms
  // Author: Bill Erickson
  // URL: http://www.billerickson.net/code/hide-empty-fields-get-form/
  	// Change 'form' to class or ID of your specific form
    var $form_selector = "#changelist-search"
	$($form_selector).submit(function() {
		$(this).find(":input").filter(function(){ return !this.value; }).attr("disabled", "disabled");
		return true; // ensure form still submits
	});
	
	// Un-disable form fields when page loads, in case they click back after submission
	$( "form" ).find( ":input" ).prop( "disabled", false );
	
});
