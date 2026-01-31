from dataclasses import dataclass, field, asdict
from pathlib import Path

import astropy.units as u
from astropy.time import Time
from anywidget import AnyWidget
from traitlets import Unicode, Float, observe, default, Bool
import logging
import numpy as np
from astropy.coordinates import SkyCoord
import ipywidgets as widgets

from .messages import *
from .imagery import get_imagery_layers
from .layers import TableLayer, LayerManager

bundler_output_dir = Path(__file__).parent / "static"

DEFAULT_SURVEYS_URL = "https://gist.githubusercontent.com/Carifio24/e8b02488d43a0e4381648fe06c100739/raw/surveys.xml"
R2D = 180 / np.pi
R2H = 12 / np.pi

logger = logging.getLogger("pywwt")


class WWTWidget(AnyWidget):
    _esm = bundler_output_dir / "main.js"
    _css = bundler_output_dir / "style.css"

    background = Unicode(
        "Hydrogen Alpha Full Sky Map",
        help="The layer to show in the background (`str`)",
    )

    foreground = Unicode(
        "Digitized Sky Survey (Color)",
        help="The layer to show in the foreground (`str`)",
    )

    foreground_opacity = Float(
        0.8, help="The opacity of the foreground layer " "(`float`)"
    )
    
    mounted = Bool(False, help="Whether the widget is mounted (`bool`)").tag(sync=True)

    # View state that the frontend sends to us:
    _raRad = 0.0
    _decRad = 0.0
    _fovDeg = 60.0
    _rollDeg = 0.0
    _engineTime = Time("2017-03-09T12:30:00", format="isot")
    _systemTime = Time("2017-03-09T12:30:00", format="isot")
    _timeRate = 1.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_queue = []
        self._on_ready = []
        self.on_msg(self._on_app_message_received)

        self._callbacks = {}
        self._futures = []

        self._available_layers = get_imagery_layers(DEFAULT_SURVEYS_URL)
        self.load_image_collection()

        self.layers = LayerManager(parent=self)
        self.current_mode = "sky"
        self.observe(self._on_mounted_change, names='mounted')

    def _send_msg(self, **kwargs):
        """
        Translate PyWWT-style raw dict messages to structured message classes.
        """
        msg_cls = msg_ref[kwargs["event"]]
        self.send(msg_cls(**kwargs))

    def send(self, msg: RemoteAPIMessage, buffers=None):
        if self.mounted:
            super().send(asdict(msg), buffers)
        else:
            self.message_queue.append({'msg':msg, 'buffers':buffers})

    def load_image_collection(self, url=DEFAULT_SURVEYS_URL):
        self.send(LoadImageCollectionMessage(url))
    
    def _on_mounted_change(self, change):
        while self.message_queue:
            message = self.message_queue.pop(0)
            self.send(message['msg'], message['buffers'])
            
        callbacks = self._on_ready
        if callbacks:
            for callback in callbacks:
                callback()
    
    def on_ready(self, callback):
        """
        Set a callback function that will be executed when the widget receives
        the "wwt_ready" message indicating the WWT application is ready to recieve
        messages.
        
        Useful for defining intialization actions that require the WWT application
        """
        self._on_ready.append(callback)
    
    def ensure_mounted(self, callback):
        # add to wwt_ready callback as a list
        if self.mounted:
            print('already mounted: running callback')
            callback()
            return
        print('not mounted: adding callback')
        self._on_ready.append(callback)
    
    @observe("foreground")
    def _on_foreground_change(self, changed):
        self.send(SetForegroundByNameMessage(name=changed["new"]))

        self.send(
            SetForegroundByOpacityMessage(
                value=self.foreground_opacity * 100,
            )
        )

    @observe("background")
    def set_background_image(self, changed):
        self.send(SetBackgroundByNameMessage(name=changed["new"]))

        self.send(
            SetForegroundByOpacityMessage(
                value=self.foreground_opacity * 100,
            )
        )

    def center_on_coordinates(self, coord, fov=60 * u.deg, roll=None, instant=True):
        """
        Navigate the camera to the specified position, asynchronously.

        Parameters
        ----------
        coord : `~astropy.units.Quantity`
            The set of coordinates the view should center on.
        fov : `~astropy.units.Quantity`, optional
            The desired field of view.
        roll: `~astropy.units.Quantity`, optional
            The desired roll angle of the camera. If not specified, the
            roll angle is not changed.
        instant : `bool`, optional
            Whether the view changes instantly or smoothly scrolls to the
            desired location.
        """
        coord_icrs = coord.icrs

        msg = CenterOnCoordinatesMessage(
            ra=coord_icrs.ra.deg,
            dec=coord_icrs.dec.deg,
            fov=fov.to(u.deg).value,
            instant=instant,
        )

        self.send(msg)

    def get_center(self):
        """
        Return the view's current right ascension and declination in degrees.
        """
        return SkyCoord(
            self._raRad * R2H,
            self._decRad * R2D,
            unit=(u.hourangle, u.deg),
        )

    def get_fov(self):
        return self._fovDeg * u.deg

    def get_roll(self):
        return self._rollDeg * u.deg

    def _on_app_message_received(self, instance, payload, buffers=None):
        """
        Call this function when a message is received from the research app.
        This will generally happen in some kind of asynchronous event handler,
        so there is no guarantee that exceptions raised here will be exposed to
        the user.
        """

        ptype = payload.get("type")
        # some events don't have type but do have:
        # pevent = payload.get('event')

        updated_fields = []

        if ptype == "wwt_view_state":
            try:
                self._raRad = float(payload["raRad"])
                self._decRad = float(payload["decRad"])
                self._fovDeg = float(payload["fovDeg"])
                self._rollDeg = float(payload["rollDeg"])
                self._engineTime = Time(payload["engineClockISOT"], format="isot")
                self._systemTime = Time(payload["systemClockISOT"], format="isot")
                self._timeRate = float(payload["engineClockRateFactor"])
            except ValueError:
                pass  # report a warning somehow?
        elif ptype == "wwt_application_state":
            hipscat = payload.get("hipsCatalogNames")

            if hipscat is not None:
                self._available_hips_catalog_names = hipscat

        elif ptype == "wwt_selection_state":
            most_recent = payload.get("mostRecentSource")
            sources = payload.get("selectedSources")

            if most_recent is not None:
                self._most_recent_source = most_recent
                updated_fields.append("most_recent_source")

            if sources is not None:
                self._selected_sources = sources
                updated_fields.append("selected_sources")

        # Any relevant async future to resolve?

        tid = payload.get("threadId")

        if tid is not None:
            try:
                fut = self._futures.pop(tid)
            except KeyError:
                pass
            else:
                fut.set_result(payload)

        # Any client-side callbacks to execute?

        callback = self._callbacks.get(ptype)

        if callback:
            try:
                callback(self, updated_fields)
            except:  # noqa: E722
                logger.exception("unhandled Python exception during a callback")

    def _set_message_type_callback(self, ptype, callback):
        """
        Set a callback function that will be executed when the widget receives
        a message with the given type.

        Parameters
        ----------
        ptype: str
            The string that identifies the message type
        callback: `BaseWWTWidget`
            A callable object which takes two arguments: the WWT widget
            instance, and a list of updated properties.
        """
        self._callbacks[ptype] = callback

    def set_selection_change_callback(self, callback):
        """
        Set a callback function that will be executed when the widget receives
        a selection change message.

        Parameters
        ----------
        callback:
            A callable object which takes two arguments: the WWT widget
            instance, and a list of updated properties.
        """
        self._set_message_type_callback("wwt_selection_state", callback)

    _most_recent_source = None

    @property
    def most_recent_source(self):
        """
        The most recent source selected in the viewer, represented as a dictionary.
        The items of this dictionary match the entries of the Source object detailed
        `here <https://docs.worldwidetelescope.org/webgl-reference/latest/apiref/research-app-messages/interfaces/selections.source.html>`_.
        """
        return self._most_recent_source

    _selected_sources = []

    @property
    def selected_sources(self):
        """
        A list of the selected sources, with each source represented as a dictionary.
        The items of these dictionaries match the entries of the Source object detailed
        `here <https://docs.worldwidetelescope.org/webgl-reference/latest/apiref/research-app-messages/interfaces/selections.source.html>`_.
        """
        return self._selected_sources

    def reset_view(self):
        """
        Reset the current view mode's coordinates and field of view to
        their original states.
        """
        if self.current_mode == "sky":
            self.center_on_coordinates(
                SkyCoord(0.0, 0.0, unit=u.deg), fov=60 * u.deg, instant=False
            )
        if self.current_mode == "planet":
            self.center_on_coordinates(
                SkyCoord(35.55, 11.43, unit=u.deg), fov=40 * u.deg, instant=False
            )
        if self.current_mode == "solar system":
            self.center_on_coordinates(
                SkyCoord(0.0, 0.0, unit=u.deg), fov=50 * u.deg, instant=False
            )
        if self.current_mode == "milky way":
            self.center_on_coordinates(
                SkyCoord(114.85, -29.52, unit=u.deg), fov=6e9 * u.deg, instant=False
            )
        if self.current_mode == "universe":
            self.center_on_coordinates(
                SkyCoord(16.67, 37.72, unit=u.deg), fov=1e14 * u.deg, instant=False
            )
        if self.current_mode == "panorama":
            pass

    def clear_tile_cache(self):
        self.send(ClearTileCacheMessage())

    @default("layout")
    def _default_layout(self):
        return widgets.Layout(height="400px", align_self="stretch")
