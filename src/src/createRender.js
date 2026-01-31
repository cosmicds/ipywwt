import * as wwtlib from "@wwtelescope/engine";
import { classicPywwt } from "@wwtelescope/research-app-messages";

const ReferenceFramesRadius = {
    Sky: 149500000000,
    Sun: 696000000,
    Mercury: 2439700,
    Venus: 6051800,
    Earth: 6371000,
    Mars: 3390000,
    Jupiter: 69911000,
    Saturn: 58232000,
    Uranus: 25362000,
    Neptune: 24622000,
    Pluto: 1161000,
    Moon: 1737100,
    Io: 1821500,
    Europa: 1561000,
    Ganymede: 2631200,
    Callisto: 2410300
};

export function createRender(app) {
	return ({ model, el }) => {
        // let _appUrl = location.toString();
        // let _appOrigin = _appUrl.origin;
        //
        // let iframe = document.createElement('iframe');
        // // Pass our origin so that the iframe can validate the provenance of the
        // // messages that are posted to it. This isn't acceptable for real XSS
        // // prevention, but so long as the research app can't do anything on behalf
        // // of the user (which it can't right now because we don't even have
        // // "users"), that's OK.
        // // iframe.src = _appUrl + '?origin=' + encodeURIComponent(location.origin);
        // iframe.style.setProperty('height', '400px', '');
        // iframe.style.setProperty('width', '100%', '');
        // iframe.style.setProperty('border', 'none', '');

        let div = document.createElement('div');
        div.setAttribute("id", "app-wrapper");
        // div.appendChild(iframe)
        div.style.setProperty('height', '400px', '');
        div.style.setProperty('width', '100%', '');
        div.style.setProperty('border', 'none', '');

        // iframe.contentWindow.document.body.appendChild(div);
        
        let mounted = model.get("mounted");

        el.appendChild(div);

        let vm = app.mount(div);

        window.vm = vm;

        vm.layers = {};

        // Setup custom message handling
        model.on("msg:custom", (msg) => {
            let layerId = null;
            let proxyLayer = null;
            let layer = null;
            let event = null;

            switch (msg.event) {
                case "center_on_coordinates":
                    console.log(classicPywwt.isCenterOnCoordinatesMessage(msg));
                    window.postMessage(msg);
                    break;
                case "table_layer_create":
                    console.log('table_layer_create',msg);
                    window.postMessage(msg);
                    break;
                case "table_layer_update":
                    // [layerId, proxyLayer] = Object.entries(vm.wwtSpreadSheetLayers).filter( ([key, item]) => item.name === msg['id']).at(0);
                    // layer = vm.spreadSheetLayerById(layerId);
                    //
                    // vm.updateTableLayer({
                    //     'dataCsv': atob(msg['table']),
                    //     'id': layer.id.toString()})

                    window.postMessage(msg);
                    break;
                case "table_layer_set":
                    [layerId, proxyLayer] = Object.entries(vm.wwtSpreadSheetLayers).filter( ([key, item]) => item.name === msg['id']).at(0);
                    layer = vm.spreadSheetLayerById(layerId);

                    let name = msg['setting'];
                    let value = null;

                    //if (name.includes('Column')) { // compatability issues?
                    if (name.indexOf('Column') >= 0) {
                        value = layer.get__table().header.indexOf(msg['value']);
                    } else if (name == 'color') {
                        // value = wwtlib.Color.fromHex(msg['value']);
                        value = msg['value']; // expects a hex string
                    } else if (name == 'colorMapper') {
                        value = wwtlib.ColorMapContainer.fromArgbList(msg['value']);
                    } else if (name == 'altUnit') {
                        value = wwtlib.AltUnits[msg['value']];
                    } else if (name == 'raUnits') {
                        value = wwtlib.RAUnits[msg['value']];
                    } else if (name == 'altType') {
                        // Assigned a default for altType since it appears one never gets passed
                        value = wwtlib.AltTypes[msg['value'] || 'altitude'];
                    } else if (name == 'plotType') {
                        value = wwtlib.PlotTypes[msg['value']];
                    } else if (name == 'markerScale') {
                        // value = wwtlib.MarkerScales[msg['value']];
                        value = msg['value']; // expects a string world/screen
                    } else if (name == 'coordinatesType') {
                        value = wwtlib.CoordinatesTypes[msg['value']];
                    } else if (name == 'cartesianScale') {
                        value = wwtlib.AltUnits[msg['value']];
                    } else {
                        value = msg['value']
                    }

                    msg['value'] = value;
                    window.postMessage(msg);
                    break;
                case 'table_layer_remove':
                    layer = vm.layers[msg['id']];
                    window.postMessage(msg);
                    break;
                case "load_image_collection":
                    window.postMessage(msg);
                    break;
                case "set_foreground_by_name":
                    window.postMessage(msg);
                    break;
                case "set_background_by_name":
                    window.postMessage(msg);
                    break;
                case "set_foreground_opacity":
                    window.postMessage(msg);
                    break;
                case "clear_tile_cache":
                    window.postMessage(msg);
                    break;
                default:
                    console.log(`Received uncaught custom message of type ${msg.event}.`)
            }
        })

        // Forward events from within the Vue app to the python model
        window.addEventListener(
            "message",
            (event) => {
                if (event.data.event === "research_app_ready") {
                    console.log("Research app ready");
                    model.set("mounted", true);
                    model.save_changes();
                    return ;
                }
                model.send(event.data);
            }, false);

		return () => app.unmount();
	};
}
