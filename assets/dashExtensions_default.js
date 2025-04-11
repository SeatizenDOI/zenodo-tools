window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, layer, context) {
            let footprint_data = feature.area ? `<b>Surface : ${feature.area}</b><br>` : ``
            footprint_data += feature.perimeter ? `<b>Length : ${feature.perimeter}</b><br>` : ``

            layer.bindTooltip(
                `<h6> ${feature.name} </h6><br>
                    ${footprint_data}
                    <b>Acquisition date : ${feature.date}</b><br>
                    <b>Platform type : ${feature.platform}</b><br>
                    <b>DOI : ${feature.doi}</b
                `)
        }

    }
});