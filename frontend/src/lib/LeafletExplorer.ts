import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-fullscreen";
import "leaflet-fullscreen/dist/leaflet.fullscreen.css";
import "leaflet-splitmap";

import { type EdnaDataType, DEFAULT_COORDS } from "./definition";

class LeafletExplorer extends HTMLElement {
    is_split: boolean;
    map: L.Map;
    splitControl: any;
    right_side: Record<string, L.TileLayer>;
    left_side: Record<string, L.TileLayer>;

    constructor() {
        super();

        this.is_split = true;
        this.right_side = {};
        this.left_side = {};

        const [lat, lng, zoom] = this.get_url_parameters();

        this.map = L.map("map-explorer", {
            // @ts-ignore (no correct types)
            fullscreenControl: true,
            minZoom: 5,
        }).setView([lat, lng], zoom);

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

        this.splitControl = L.control // @ts-ignore (no correct types)
            .splitMap(Object.values(this.left_side), Object.values(this.right_side))
            .addTo(this.map);

        this.setup_event();
        this.load_edna_data();
    }

    // Show or hide the split pan.
    toggle_split_map() {
        if (this.is_split) {
            this.map.removeControl(this.splitControl);
        } else {
            this.splitControl = L.control // @ts-ignore (no correct types)
                .splitMap(Object.values(this.left_side), Object.values(this.right_side))
                .addTo(this.map);
        }
        this.is_split = !this.is_split;
    }

    clear_layer(side: "left" | "right") {
        const sideLayers = side === "left" ? this.left_side : this.right_side;
        for (const layer of Object.values(sideLayers)) {
            this.map.removeLayer(layer);
        }
        if (side === "left") this.left_side = {};
        else this.right_side = {};
    }

    // Add layers
    update_layers(side_id: string, layers_code: string[]) {
        // Each time we redraw the splitlane.
        this.map.removeControl(this.splitControl);

        // Remove all the layer at the left or the right.
        this.clear_layer(side_id.includes("left") ? "left" : "right");

        // For each code, we create a new tile.
        layers_code.forEach((code) => {
            const ly = code.split("_");

            const url = `https://tmsserver.ifremer.re/wmts?request=GetTile&layer=${ly[0]}&year=${ly[1]}&tilematrix={z}&tilerow={x}&tilecol={y}`; // TODO Change this URL

            // Build the tile with the URL.
            const tile = L.tileLayer(url, {
                attribution: "&copy; Ifremer DOI",
                minZoom: 5,
                maxZoom: 28,
            }).addTo(this.map);

            // keep track of the tile.
            if (side_id.includes("left")) this.left_side[code] = tile;
            else this.right_side[code] = tile;
        });

        // Re draw the split lane.
        this.splitControl = L.control // @ts-ignore (no correct types)
            .splitMap(Object.values(this.left_side), Object.values(this.right_side))
            .addTo(this.map);
    }

    async load_edna_data() {
        try {
            const response = await fetch("/edna_data.json");
            if (!response.ok) {
                throw new Error("EDNA Data not found");
            }

            const edna_data: EdnaDataType[] = await response.json();

            edna_data.forEach((edna) => {
                const popup = new L.Popup({
                    content: `
            <h3>${edna.place} - ${edna.date}</h3>
            <b>Position:</b> ${edna.GPSLatitude}, ${edna.GPSLongitude}<br>
            <b>Publication:</b> <a href="${edna.publication.link}" target="_blank"> ${edna.publication.name}</a><br>
            <b>Data:</b> <a href="${edna.data.link}" target="_blank"> ${edna.data.name}</a><br>
            <b>Description:</b> ${edna.description}<br>
            <img src="${edna.thumbnail}" width="600">`,
                    maxWidth: 600,
                    closeOnClick: true,
                    autoClose: true,
                    closeButton: true,
                });

                const marker = L.marker([Number(edna.GPSLatitude), Number(edna.GPSLongitude)])
                    .addTo(this.map)
                    .bindPopup(popup);
                marker.on("popupopen", () => {
                    const popupLatLng = marker.getPopup()?.getLatLng();
                    if (!popupLatLng) {
                        return;
                    }

                    // Project the popup's lat/lng to pixel coordinates
                    const point = this.map.project(popupLatLng, this.map.getZoom());

                    // Offset upward by N pixels (e.g., 150px)
                    point.y -= 350;

                    // Convert back to lat/lng
                    const newLatLng = this.map.unproject(point, this.map.getZoom());

                    // Smooth pan to adjusted center
                    this.map.panTo(newLatLng, {
                        animate: true,
                        duration: 0.5,
                    });
                });
            });
        } catch (error) {
            console.error("There has been a problem with your fetch operation:", error);
        }
    }

    get_url_parameters(): [number, number, number] {
        const url = new URL(window.location.href);
        const lat = Number(url.searchParams.get("lat") ?? DEFAULT_COORDS.lat);
        const lng = Number(url.searchParams.get("lng") ?? DEFAULT_COORDS.lng);
        const zoom = Number(url.searchParams.get("zoom") ?? DEFAULT_COORDS.zoom);

        return [lat, lng, zoom];
    }

    setup_event() {
        this.map.on("moveend", (e) => {
            const url = new URL(window.location.href);
            url.searchParams.set("lat", this.map.getCenter()["lat"].toFixed(6).toString());
            url.searchParams.set("lng", this.map.getCenter()["lng"].toFixed(6).toString());
            url.searchParams.set("zoom", this.map.getZoom().toString());

            window.history.replaceState({}, "", url);
        });
    }
}

window.customElements.define("leaflet-explorer", LeafletExplorer);
