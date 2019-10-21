googleMe = function(field_name){
	var ele_name = "id_".concat(field_name);
    var val = document.getElementById(ele_name).value;
    val = val.replace(/ /g,"+");
    var url = "https://www.google.de/search?q=".concat(val);
   	if(val){
    	window.open(url,"_blank");
    }
};
