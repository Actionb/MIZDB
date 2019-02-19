/*global gettext*/
(function($) {
    'use strict';
    $(document).ready(function() {
        // Add anchor tag for Show/Hide
        $("fieldset.collapse").each(function(i, elem) {
            var has_error = $(elem).find("div.errors").length !== 0;
            var is_collapsed = $(elem).hasClass('collapsed');
            // Don't hide if fields in this fieldset have errors
            if (has_error && is_collapsed) { 
                $(elem).removeClass('collapsed'); 
            }
            var label_text = gettext("Hide");
            if($(elem).hasClass("collapsed")){
                label_text = gettext("Show");
            }
            var hint = '<span class="collapse-hint">' + '(' + label_text + ')' +'</span>';
            if ($(elem).hasClass("stacked-inline-collapsible")){
                $(elem).siblings("h3").first().prepend('<span class="collapse-hint" style="float:left;">' + '(' + label_text + ')' +'</span>')//.children().last().before(hint);
            }
            else {
                $(elem).find("h2").first().append(hint);
            }
        });
        
        $(".collapsible").click(function(){
            // find out which element to collapse:
            // either a direct parent fieldset element (inlines, fieldsets) or a sibling with class .collapse (inside stacked inlines)
            var elem = $(this).parent();
            if (!elem.hasClass("collapse")){
                // parent does not have class collapse, so we need to look for a sibling with that class instead
                elem = $(this).siblings(".collapse");
            }
            if(elem.hasClass("collapsed")){
                $(this).children(".collapse-hint").text('('+gettext("Hide")+')');
            }
            else {
                $(this).children(".collapse-hint").text('('+gettext("Show")+')');
            }
            elem.toggleClass("collapsed");
        });
    });
})(django.jQuery);
