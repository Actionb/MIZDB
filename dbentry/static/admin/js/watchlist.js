
django.jQuery(document).ready(function($){

    /* Update the changelist link upon removal of a watchlist item. */
    function updateLink(removed){
        let container = removed.parents(".model-container")
        let link = container.find(".cl-button");
        let url = link.attr("href").split("=")[0];
        let ids = "";
        // Gather the IDs - except for the one of the removed item.
        container.find(".watchlist-remove").each(function(){
            if (this.dataset.id == removed.get(0).dataset.id){
                return
            }
            if (ids == "") {
                ids = this.dataset.id;
            } else {
                ids += "," + this.dataset.id;
            }
        })
        link.attr("href", url + "=" + ids);
    }

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

    /* watchlist overview changelist button */
    $(".cl-button").click(function(event){
       let container = $(this).parents(".model-container");
       let url = $(this).attr("href").split("=")[0];
       let ids = "";
       // Gather the IDs - except for the one of the removed item.
       container.find(".watchlist-remove").each(function(){
           if (ids == "") {
               ids = this.dataset.id;
           } else {
               ids += "," + this.dataset.id;
           }
       })
       $(this).attr("href", url + "=" + ids)
    });

    $(".cl-button").on("mouseup", function(event){
        // There is no 'click' event for middle mouse clicks.
        // Handle middle mouse button (2) releases like left clicks:
        if (event.which == 2){
            event.preventDefault();
            $(this).click();
        }
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
                // updateLink(element);
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

