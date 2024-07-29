window.dccFunctions = window.dccFunctions || {};
window.dccFunctions.markToDate = function (value) {
    month = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    return month[value % 12];

}