window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, layer, context) {
            layer.bindTooltip(`<h6> ${feature.name} </h6><br>
                               <b>Surface : ${feature.area}</b><br>
                               <b>Acquisition date : ${feature.date}</b><br>
                            <b>Platform type : ${feature.platform}</b><br>
                                 <b>DOI : ${feature.doi}</b
                                 `)
        }
    }
});