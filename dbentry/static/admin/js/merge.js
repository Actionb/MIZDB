(function($) {
    $(document).ready(function(){
        $("#action-toggle").css("display", "none");  // hide the 'select all' checkbox
        $('input[type="checkbox"]').filter(".action-select").on('change', function() {
            // Store the last selected value in the hidden form field:
            $('#id_0-primary').val($(this).val());
            // Uncheck the other checkboxes and 'un-highlight' their parent row:
            $('input[type="checkbox"]').filter(".action-select").not(this).each(function() {
                $(this).prop('checked', false);
                $(this).parents('tr').removeClass('selected');
            });
        });
    });
})(django.jQuery);