window.dccFunctions = window.dccFunctions || {};
window.dccFunctions.markToDate = function (value) {
    month = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    return month[value % 12];

}

const color = {
    "ASV": "#AFA4CE",
    "UAV": "#47EAD0",
    "SCUBA": "#FCFE19",
    "PADDLE": "#FE277E"
}

window.PlatformSpace = Object.assign({}, window.PlatformSpace, {
    PlatformSpaceColor: {
        platformToColorMap: function (geojson) {
            return { 'color': color[geojson.platform] }
        }
    }
});