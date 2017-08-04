var $ = django.jQuery;
$('form#adv-changelist-search').submit(function() {

    $(".inp-gte").each(
        function() {
            if($(this).val()!="") {
                if($(this).next().val()=="") {
                    name_len = $(this).attr('name').length;
                    $(this).attr('name', $(this).attr('name').slice(0,name_len-5));
                    $(this).next().attr('name','');
                }
            }
            else {
                $(this).attr('name','');
            }
        }
    );
    $("input").filter(
        function() {
            return $(this).val()=='';
        }
    ).attr('name','');
        
    $("select").each(
        function() {
            if ($(this).children().filter(":selected").val()=="") {
                $(this).attr('name','');
            }
        }
    );
});


