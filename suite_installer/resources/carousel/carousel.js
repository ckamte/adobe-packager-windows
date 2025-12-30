$(document).ready(function () {
    cecInit();
})

function cecInit() {
    var jsonData;
	var	locale = getParameterByName('locale');
    var isHighDpi = getParameterByName('isHighDpi');
	cecGetLocaleJson(locale);
}

function resizeWin() {
	myWindow.resizeTo(455, 239);	
	
	}
var slideIndex = 0;
showSlides();

function showSlides() {
    var i;
    var slides = document.getElementsByClassName("mySlides");
   for (i = 0; i < slides.length; i++) {
       console.log(slides[i]);
       slides[i].style.opacity = "0";
       slides[i].style.visibility = "hidden";
    }
    slideIndex++;
    if (slideIndex > slides.length) {slideIndex = 1}

    slides[slideIndex-1].style.opacity = "1";
	slides[slideIndex-1].style.visibility = "visible";

	var x = document.getElementsByTagName('video');
    if (slideIndex == 1) {
      x[0].currentTime = 0;
    } 
    setTimeout(showSlides, 17500); // Change image every 17.50 seconds
}

function getParameterByName(name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
        results = regex.exec(location.search);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function cecGetLocaleJson(locale)
{
	console.log("cecGetLocaleJson");
	var jsonLocation = "Dictionary/" + locale + "/locale.json";
	
	$.getJSON(jsonLocation, function (data) { 
		cecDisplayContent(data, locale);
    })
    .fail(function () {     
      if(locale == "en_US") {
		  return;
	  }
	  cecGetLocaleJson("en_US");
    })
}

function cecDisplayContent(data, locale)
{
	var lcl = locale.slice(3,5);
	var url = "http://www.adobe.com/"+lcl.toLowerCase()+"/creativecloud.html";
	if(locale == "en_us" || locale == "en_US") {
		  url = "http://www.adobe.com/creativecloud.html";
	  }
	document.getElementById("slideContainer").onclick =function() { parent.cecExternalLink(url) };
	document.getElementById("slideText1").innerHTML = data["TextSlide1"];
}