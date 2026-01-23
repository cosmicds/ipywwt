"""
Example usage of ipywwt in a solara app. Run with:
    solara run notebooks/solara.py
"""

import solara
from ipywwt import WWTWidget
from solara.alias import rv
from astropy.table import Table
from astropy.coordinates import SkyCoord
import astropy.units as u

# wwt1 = WWTWidget()
# wwt2 = WWTWidget()
# button = w.Button(description="Clicked 0 times")
# page = w.VBox([wwt1, wwt2, button])


@solara.component
def Page():
    add_layer = solara.use_reactive(False)
    coord_ra = solara.use_reactive(0.0)
    coord_dec = solara.use_reactive(0.0)
    coord_fov = solara.use_reactive(310.0)
    adjust_layer_color = solara.use_reactive("#00FF00")
    adjust_layer_size = solara.use_reactive(100)
    show_constellation_boundaries = solara.use_reactive(True)
    show_constellation_figures = solara.use_reactive(True)
    selected_background_layer = solara.use_reactive("Hydrogen Alpha Full Sky Map")
    selected_foreground_layer = solara.use_reactive("Digitized Sky Survey (Color)")
    foreground_opacity = solara.use_reactive(1.0)
    all_layers = solara.use_reactive([])
    is_wwt_ready = solara.use_reactive(False)

    with rv.Container():
        with rv.Row():
            with rv.Col():
                with rv.Card():
                    with rv.CardTitle():
                        solara.Text("WWT Widget Test")

                    with rv.CardText():
                        rv.Alert(
                            children=[
                                f"WWT research app is {'' if is_wwt_ready.value else 'NOT '}ready."
                            ],
                            type="info" if is_wwt_ready.value else "warning",
                        )

                        wwt_container = rv.Html(tag="div")

        with rv.Row():
            with rv.Col():
                with solara.Row(classes=["mb-2"]):
                    solara.InputFloat(
                        "RA", value=coord_ra.value, on_value=lambda v: coord_ra.set(v)
                    )
                    solara.InputFloat(
                        "Dec",
                        value=coord_dec.value,
                        on_value=lambda v: coord_dec.set(v),
                    )

                with solara.Row():
                    solara.FloatSlider(
                        "FOV",
                        value=coord_fov.value,
                        on_value=lambda v: coord_fov.set(v),
                        min=0,
                        max=60,
                        step=5,
                    )

            with rv.Col():
                with solara.Row():
                    solara.Button(
                        "Load Layer",
                        on_click=lambda: add_layer.set(True),
                    )

                with solara.Row(classes=["mt-2"]):
                    rv.ColorPicker(
                        v_model=adjust_layer_color.value,
                        on_v_model=lambda v: adjust_layer_color.set(v),
                    )

                solara.Text(text=f"Layer Color: {adjust_layer_color.value}")

                with solara.Row(classes=["mt-2"]):
                    solara.FloatSlider(
                        "Marker Size",
                        value=adjust_layer_size.value,
                        on_value=lambda v: adjust_layer_size.set(v),
                        min=0,
                        max=200,
                        step=10,
                    )

            with rv.Col():
                with solara.Row():
                    solara.Checkbox(
                        label="Show Constellation Boundaries",
                        value=show_constellation_boundaries.value,
                        on_value=lambda v: show_constellation_boundaries.set(v),
                    )

                    solara.Checkbox(
                        label="Show Constellation Figures",
                        value=show_constellation_figures.value,
                        on_value=lambda v: show_constellation_figures.set(v),
                    )

                with solara.Row():
                    solara.Select(
                        label="Foreground Layer",
                        values=all_layers.value,
                        value=selected_foreground_layer.value,
                        on_value=lambda v: selected_foreground_layer.set(v),
                    )

                with solara.Row():
                    solara.FloatSlider(
                        label="Foreground Opacity",
                        value=foreground_opacity.value,
                        on_value=lambda v: foreground_opacity.set(v),
                        min=0,
                        max=1,
                        step=0.1,
                    )

                with solara.Row(classes=["mt-2"]):
                    solara.Select(
                        label="Background Layer",
                        values=all_layers.value,
                        value=selected_background_layer.value,
                        on_value=lambda v: selected_background_layer.set(v),
                    )

    def _add_widget():
        # The `use_remote` parameter will toggle between using the remote WWT
        #  server and the local WWT server.
        wwt_widget = WWTWidget(use_remote=True)
        all_layers.set(wwt_widget.available_layers)

        wwt_widget_container = solara.get_widget(wwt_container)
        wwt_widget_container.children = (wwt_widget,)

        wwt_widget.observe(lambda c: is_wwt_ready.set(c["new"]), names=["_wwt_ready"])

        def cleanup():
            wwt_widget_container.children = ()
            wwt_widget.close()

        return cleanup

    solara.use_effect(_add_widget, dependencies=[])

    def _add_layer():
        if not add_layer.value:
            return

        wwt_widget = solara.get_widget(wwt_container).children[0]

        OEC = "https://worldwidetelescope.github.io/pywwt/data/open_exoplanet_catalogue.csv"
        table = Table.read(OEC, delimiter=",", format="ascii.basic")

        layer = wwt_widget.layers.add_table_layer(
            frame="Sky", table=table, lon_att="ra", lat_att="dec"
        )
        layer.size_scale = 100

    solara.use_effect(_add_layer, dependencies=[add_layer.value])

    def _center_on_coordinates():
        wwt_widget = solara.get_widget(wwt_container).children[0]
        wwt_widget.center_on_coordinates(
            SkyCoord(coord_ra.value * u.deg, coord_dec.value * u.deg),
            fov=coord_fov.value * u.deg,
        )

    solara.use_effect(
        _center_on_coordinates,
        dependencies=[coord_ra.value, coord_dec.value, coord_fov.value],
    )

    def _adjust_color():
        if not add_layer.value:
            return

        wwt_widget = solara.get_widget(wwt_container).children[0]
        wwt_widget.layers[0].color = adjust_layer_color.value

    solara.use_effect(_adjust_color, dependencies=[adjust_layer_color.value])

    def _adjust_marker_size():
        if not add_layer.value:
            return

        wwt_widget = solara.get_widget(wwt_container).children[0]
        wwt_widget.layers[0].size_scale = adjust_layer_size.value

    solara.use_effect(_adjust_marker_size, dependencies=[adjust_layer_size.value])

    def _constellation_settings():
        wwt_widget = solara.get_widget(wwt_container).children[0]
        wwt_widget.constellation_boundaries = show_constellation_boundaries.value
        wwt_widget.constellation_figures = show_constellation_figures.value

    solara.use_effect(
        _constellation_settings,
        dependencies=[
            show_constellation_boundaries.value,
            show_constellation_figures.value,
        ],
    )

    def _set_foreground():
        wwt_widget = solara.get_widget(wwt_container).children[0]

        wwt_widget.foreground = selected_foreground_layer.value
        wwt_widget.foreground_opacity = foreground_opacity.value

    solara.use_effect(
        _set_foreground,
        dependencies=[selected_foreground_layer.value, foreground_opacity.value],
    )

    def _set_background():
        wwt_widget = solara.get_widget(wwt_container).children[0]
        wwt_widget.background = selected_background_layer.value

    solara.use_effect(_set_background, dependencies=[selected_background_layer.value])
