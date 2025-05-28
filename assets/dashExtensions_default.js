window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function explorer(feature, layer, context) {
                const popupContent = `
                    <h6>${feature.place} - ${feature.date}</h6>
                    <b>Position:</b> ${feature.GPSLatitude}, ${feature.GPSLongitude}<br>
                    <b>Publication:</b> <a href="${feature.publication_link}" target="_blank"> ${feature.publication_name}</a><br>
                    <b>Data:</b> <a href="${feature.data_link}" target="_blank"> ${feature.data_name}</a><br>
                    <b>Description:</b> ${feature.description}<br>
                    <img src="${feature.thumbnail}" width="600">
                `;

                layer.bindPopup(popupContent, {
                    closeOnClick: false,
                    autoClose: true,
                    closeButton: true,
                    maxWidth: 650
                });

                let popupOpen = false;
                layer.on('click', function() {
                    if (popupOpen) {
                        layer.closeTooltip();
                    } else {
                        layer.openTooltip();
                    }
                    popupOpen = !popupOpen;
                });
            }

            ,
        function1: function(feature, layer, context) {
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