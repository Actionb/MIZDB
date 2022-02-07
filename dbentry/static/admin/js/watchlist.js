
django.jQuery(document).ready(function($){
    /* change page checkbox */
    $(".watchlist-toggle").click(function(event){
        event.preventDefault();
        let element = this;
        $.get(
            url='/admin/watchlist_toggle',
            data={'id': this.dataset.id, 'model_label': this.dataset.modelLabel},
            success=function(data){ element.checked = data.on_watchlist;},
            dataType='json',
        );
    });

    /* watchlist overview checkbox */
    $(".watchlist-remove").click(function(event){
        let element = $(this);
        $.get(
            url='/admin/watchlist_toggle',
            data={
                'id': this.dataset.id,
                'model_label': this.dataset.modelLabel,
                'remove_only': true
            },
            success=function(data){
                element.parents('tr').remove();
                // TODO: what if this removes the last table row for a given model?
/*                if (element.parents('tbody').children.length > 1){
                    element.parents('tr').remove();
                }
                else {
                    // This element is the only item for this model: remove the table.
                    element.parents('table').remove()
                }*/
            },
            dataType='json',
        );
    });
});

