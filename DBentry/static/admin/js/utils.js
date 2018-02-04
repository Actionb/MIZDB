googleMe = function(p){
	var ele_name = "id_".concat(p);
    var val = document.getElementById(ele_name).value;
    val = val.replace(/ /g,"+");
    var url = "https://www.google.de/search?q=".concat(escape(val));
   	if(val){
    	window.open(url,"_blank");
    }
};
