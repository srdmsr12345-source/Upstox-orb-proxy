document.addEventListener(

"DOMContentLoaded",

function(){

const form = document.getElementById("scanForm");

if(!form) return;

form.addEventListener(

"submit",

async function(e){

e.preventDefault();

const btn =
form.querySelector("button");

btn.disabled = true;

btn.innerText = "Scanning...";

const formData =
new FormData(form);

const response =
await fetch(

"/scan",

{

method:"POST",

body:formData

}

);

const json =
await response.json();

document.getElementById(

"summary"

).innerHTML =

`<div class="alert alert-success">

<b>Total:</b> ${json.summary.total}

&nbsp;&nbsp;

<b>High:</b> ${json.summary.high}

&nbsp;&nbsp;

<b>Medium:</b> ${json.summary.medium}

&nbsp;&nbsp;

<b>Low:</b> ${json.summary.low}

</div>`;

const thead =
document.getElementById("thead");

const tbody =
document.getElementById("tbody");

thead.innerHTML="";

tbody.innerHTML="";

if(json.data.length===0){

tbody.innerHTML=

"<tr><td>No Result</td></tr>";

btn.disabled=false;

btn.innerText="Scan";

return;

}

Object.keys(

json.data[0]

).forEach(col=>{

thead.innerHTML +=

`<th>${col}</th>`;

});

json.data.forEach(row=>{

let tr="<tr>";

Object.values(row)

.forEach(val=>{

tr += `<td>${val}</td>`;

});

tr+="</tr>";

tbody.innerHTML += tr;

});

btn.disabled=false;

btn.innerText="Scan";

});

});
