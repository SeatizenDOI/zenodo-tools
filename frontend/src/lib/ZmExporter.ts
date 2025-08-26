import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-fullscreen";
import "leaflet-fullscreen/dist/leaflet.fullscreen.css";
import "leaflet-measure";
import "leaflet-measure/dist/leaflet-measure.css";
import "leaflet-draw";
import "leaflet-draw/dist/leaflet.draw.css";

import { type EdnaDataType, DEFAULT_COORDS } from "./definition";

class ZmExporter extends HTMLElement {
    map: L.Map;

    constructor() {
        super();

        this.map = L.map("map-exporter", {
            // @ts-ignore (no correct types)
            fullscreenControl: true,
            minZoom: 5,
        }).setView([DEFAULT_COORDS.lat, DEFAULT_COORDS.lng], DEFAULT_COORDS.zoom);

        L.control.scale({ imperial: false, position: "bottomright" }).addTo(this.map);

        const background_map = L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            {
                attribution: "Tiles © Esri",
                opacity: 0.75,
            }
        ).addTo(this.map);

        const background_map2 = L.tileLayer(
            "https://{s}.basemaps.cartocdn.com/rastertiles/light_only_labels/{z}/{x}/{y}{r}.png",
            {
                attribution:
                    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            }
        ).addTo(this.map);

        // This piece of code correct a bug with leaflet-measure where the map move on click. https://github.com/ljagis/leaflet-measure/issues/171
        // @ts-ignore (no correct types)
        L.Control.Measure.include({
            // set icon on the capture marker
            _setCaptureMarkerIcon: function () {
                // disable autopan
                this._captureMarker.options.autoPanOnFocus = false;

                // default function
                this._captureMarker.setIcon(
                    L.divIcon({
                        iconSize: this._map.getSize().multiplyBy(2),
                    })
                );
            },
        });

        const measure_control = L.control
            // @ts-ignore (no correct types)
            .measure({
                position: "topleft",
                primaryLengthUnit: "meters",
                secondaryLengthUnit: "kilometers",
                primaryAreaUnit: "hectares",
                secondaryAreaUnit: "sqmeters",
                localization: "fr",
            })
            .addTo(this.map);

        const drawnItems = new L.FeatureGroup();
        this.map.addLayer(drawnItems);

        // Add draw control
        // @ts-ignore (no correct types)
        const drawControl = new L.Control.Draw({
            position: "bottomleft",
            edit: {
                featureGroup: drawnItems,
                edit: false,
            },
            draw: {
                polygon: true,
                polyline: false,
                rectangle: false,
                circle: false,
                marker: false,
                circlemarker: false,
            },
        });
        this.map.addControl(drawControl);

        // Listen to create event
        // @ts-ignore (no correct types)
        this.map.on(L.Draw.Event.CREATED, function (event: any) {
            const layer = event.layer;
            drawnItems.addLayer(layer);

            // Get GeoJSON
            console.log(layer.toGeoJSON());
        });

        this.setup_event();
    }

    setup_event() {}
}

window.customElements.define("zm-exporter", ZmExporter);
