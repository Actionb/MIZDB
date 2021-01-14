googleMe = function(field_name){
	var ele_name = "id_".concat(field_name);
    var val = encodeURIComponent(document.getElementById(ele_name).value.trim());
   	if(val){
    	window.open("https://www.google.de/search?q=".concat(val),"_blank");
    }
};
