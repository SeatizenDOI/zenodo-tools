window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, layer, context) {
            layer.bindTooltip(`<b> ${feature.name} </b>`)
        }
    }
});