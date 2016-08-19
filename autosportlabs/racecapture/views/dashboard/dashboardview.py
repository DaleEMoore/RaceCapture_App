import os
import kivy
import time
kivy.require('1.9.1')
from kivy.uix.carousel import Carousel
from kivy.uix.settings import SettingsWithNoMenu
from kivy.app import Builder
from kivy.core.window import Window, Keyboard
from kivy.logger import Logger
from kivy.clock import Clock
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import Screen
from utils import kvFindClass
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.button import Button
from autosportlabs.racecapture.views.dashboard.widgets.digitalgauge import DigitalGauge
from autosportlabs.racecapture.views.dashboard.widgets.stopwatch import PitstopTimerView
from autosportlabs.racecapture.settings.systemsettings import SettingsListener
from autosportlabs.racecapture.views.dashboard.widgets.gauge import Gauge
from autosportlabs.racecapture.views.configuration.rcp.trackselectview import TrackSelectView
from autosportlabs.racecapture.views.util.alertview import editor_popup
from autosportlabs.racecapture.config.rcpconfig import Track
from autosportlabs.racecapture.config.rcpconfig import TrackConfig
from autosportlabs.racecapture.config.rcpconfig import Capabilities

# Dashboard screens
from autosportlabs.racecapture.views.dashboard.gaugeview import GaugeView
from autosportlabs.racecapture.views.dashboard.tachometerview import TachometerView
from autosportlabs.racecapture.views.dashboard.laptimeview import LaptimeView
from autosportlabs.racecapture.views.dashboard.rawchannelview import RawChannelView
from autosportlabs.racecapture.views.dashboard.comboview import ComboView

from collections import OrderedDict
DASHBOARD_VIEW_KV = """
<DashboardView>:
    AnchorLayout:
        BoxLayout:
            orientation: 'vertical'
            Carousel:
                id: carousel
                on_current_slide: root.on_current_slide(args[1])                
                size_hint_y: 0.90
                loop: True
            BoxLayout:
                size_hint_y: 0.10
                orientation: 'horizontal'
                IconButton:
                    color: [1.0, 1.0, 1.0, 1.0]
                    font_size: self.height * 1.2
                    text: ' \357\203\231'
                    size_hint_x: 0.4
                    size_hint_y: 1.1
                    on_release: root.on_nav_left()
                DigitalGauge:
                    rcid: 'left_bottom'
                DigitalGauge:
                    rcid: 'center_bottom'
                DigitalGauge:
                    rcid: 'right_bottom'
                IconButton:
                    color: [1.0, 1.0, 1.0, 1.0]
                    font_size: self.height * 1.2
                    text: '\357\203\232 '
                    size_hint_x: 0.4
                    size_hint_y: 1.1
                    on_release: root.on_nav_right()
        AnchorLayout:
            anchor_x: 'left'
            anchor_y: 'top'
            IconButton:
                id: preferences_button
                size_hint_y: 0.1
                size_hint_x: 0.1
                text: u'\uf013'
                halign: 'left'
                color: [1.0, 1.0, 1.0, 0.2]
                on_press: root.on_preferences()
"""


class DashboardView(Screen):
    """
    The main dashboard view.
    Provides the framework for adding and managing various dashboard screens.
    """
    _POPUP_SIZE_HINT = (0.75, 0.8)
    _POPUP_DISMISS_TIMEOUT_LONG = 60.0
    Builder.load_string(DASHBOARD_VIEW_KV)

    def __init__(self, track_manager, rc_api, rc_config, **kwargs):
        self._initialized = False
        self._view_builders = OrderedDict()
        super(DashboardView, self).__init__(**kwargs)
        self.register_event_type('on_tracks_updated')
        self._databus = kwargs.get('dataBus')
        self._settings = kwargs.get('settings')
        self._track_manager = track_manager
        self._rc_api = rc_api
        self._rc_config = rc_config
        self._alert_widgets = {}
        self._dismiss_popup_trigger = Clock.create_trigger(self._dismiss_popup, DashboardView._POPUP_DISMISS_TIMEOUT_LONG)
        self._popup = None
        self._race_setup_view = None
        self._selected_track = None
        self._track_config = None

    def on_tracks_updated(self, trackmanager):
        pass

    def _init_view_builders(self):
        # Factory / builder functions for views
        # To add a new dashboard screen, add a function here for the builder
        # And add it to the dictionary below.

        def build_gauge_view():
            return GaugeView(name='gaugeView', databus=self._databus, settings=self._settings)

        def build_tachometer_view():
            return TachometerView(name='tachView', databus=self._databus, settings=self._settings)

        def build_laptime_view():
            return LaptimeView(name='laptimeView', databus=self._databus, settings=self._settings)

        def build_raw_channel_view():
            return RawChannelView(name='rawchannelView', databus=self._databus, settings=self._settings)

        def build_combo_view():
            return ComboView(name='comboView', databus=self._databus, settings=self._settings)

        builders = self._view_builders
        builders['gaugeView'] = build_gauge_view
        builders['laptimeView'] = build_laptime_view
        builders['tachView'] = build_tachometer_view
        builders['rawchannelView'] = build_raw_channel_view
        # builders['comboView'] = build_combo_view

        for i, v in enumerate(self._view_builders):
            self.ids.carousel.add_widget(AnchorLayout())

    def _init_global_gauges(self):
        databus = self._databus
        settings = self._settings

        activeGauges = list(kvFindClass(self, Gauge))

        for gauge in activeGauges:
            gauge.settings = settings
            gauge.data_bus = databus

    def _init_view(self):
        databus = self._databus
        settings = self._settings

        self._init_global_gauges()
        self._init_view_builders()

        # Find all of the global and set the objects they need
        gauges = list(kvFindClass(self, DigitalGauge))
        for gauge in gauges:
            gauge.settings = settings
            gauge.data_bus = databus

        # Initialize our alert type widgets
        self._alert_widgets['pit_stop'] = PitstopTimerView(databus, 'Pit Stop')

        self._notify_preference_listeners()
        self._show_last_view()

        if self._rc_api.connected:
            self._race_setup()

        self._rc_api.add_connect_listener(self._on_rc_connect)
        self._initialized = True

    def _on_rc_connect(self, *args):
        Clock.schedule_once(lambda dt: self._race_setup())

    def _race_setup(self):

        """
        Beginnings of a 'race setup' screen that checks everything is working and set correctly. Currently
        just checks that a track map is detected/set.
        :return:
        """
        if self._rc_api.connected:
            if not self._selected_track:

                def capabilities_fail():
                    Logger.error("DashboardView: _race_setup(), could not get capabilities to determine if device has "
                                 "a tracks db")

                def capabilities_success(capabilities_dict):
                    capabilities = Capabilities()
                    capabilities.from_json_dict(capabilities_dict['capabilities'])

                    # For devices that have no device storage, attempt to set a track
                    if capabilities.storage.tracks == 0:

                        # Now figure out if the device already has a track set, if not, set one. Enough callbacks yet?!

                        def track_fail():
                            Logger.error("DashboardView: _race_setup(), could not get track config")

                        def track_success(track_config):
                            self._track_config = TrackConfig()

                            self._track_config.fromJson(track_config['trackCfg'])
                            Logger.debug("DashboardView: _race_setup(), got track config: {}".format(self._track_config))

                            # Only clear way to know if the track in the track config is a real track or not is by
                            # checking start/finish point. If both are 0, not a track. Can't use track id because a
                            # track id of 0 can be a user defined track
                            if self._track_config.track.startLine.latitude != 0 and \
                               self._track_config.track.startLine.longitude != 0:
                                    # Prompt for track!
                                    # Scheduling once because this callback is not in the UI thread and if we update
                                    # the UI now we'll crash >:\
                                    Clock.schedule_once(lambda dt: self._load_race_setup_view())

                        self._rc_api.getTrackCfg(track_success, track_fail)

                Clock.schedule_once(lambda dt: self._rc_api.get_capabilities(capabilities_success, capabilities_fail))
            else:
                self._set_rc_track(self._selected_track)

    def _load_race_setup_view(self):
        content = TrackSelectView(self._track_manager)
        self._race_setup_view = content
        self._popup = editor_popup("Select your track", content, self._on_race_setup_close)
        self._popup.open()

    def _on_race_setup_close(self, instance, answer):
        if answer:
            self._selected_track = self._race_setup_view.selected_track
            Logger.debug("DashboardView: setting track: {}".format(self._selected_track))
            self._set_rc_track(self._selected_track, self._track_config)

        self._popup.dismiss()

    def _set_rc_track(self, track, track_config):
        new_track = Track.fromTrackMap(track)
        new_track.trackId = track.short_id
        track_config.track = new_track
        track_config.autoDetect = False
        self._rc_api.setTrackCfg(track_config.toJson())
        self._rc_api.sendFlashConfig()

        now = int(time.time())
        self._settings.userPrefs.set_last_selected_track(track.track_id, now)

    def on_enter(self):
        Window.bind(mouse_pos=self.on_mouse_pos)
        Window.bind(on_key_down=self.on_key_down)
        if not self._initialized:
            self._init_view()

    def on_leave(self):
        Window.unbind(mouse_pos=self.on_mouse_pos)
        Window.unbind(on_key_down=self.on_key_down)

    def _got_activity(self):
        self.ids.preferences_button.brighten()

    def on_touch_down(self, touch):
        self._got_activity()
        return super(DashboardView, self).on_touch_down(touch)

    def on_mouse_pos(self, x, pos):
        if self.collide_point(pos[0], pos[1]):
            self._got_activity()
            self.ids.preferences_button.brighten()
        return False

    def on_key_down(self, window, key, *args):
        if key == Keyboard.keycodes['left']:
            self.on_nav_left()
        elif key == Keyboard.keycodes['right']:
            self.on_nav_right()
        return False

    def on_preferences(self, *args):
        settings_view = SettingsWithNoMenu()
        base_dir = self._settings.base_dir
        settings_view.add_json_panel('Dashboard Preferences', self._settings.userPrefs.config, os.path.join(base_dir, 'resource', 'settings', 'dashboard_settings.json'))

        popup = ModalView(size_hint=DashboardView._POPUP_SIZE_HINT)
        popup.add_widget(settings_view)
        popup.bind(on_dismiss=self._popup_dismissed)
        popup.open()
        self._popup = popup
        # self._dismiss_popup_trigger()

    def _popup_dismissed(self, *args):
        self._notify_preference_listeners()

    def _dismiss_popup(self, *args):
        if self._popup:
            self._popup.dismiss()
            self._popup = None

    def _notify_preference_listeners(self):
        listeners = list(kvFindClass(self, SettingsListener)) + self._alert_widgets.values()
        for listener in listeners:
            listener.user_preferences_updated(self._settings.userPrefs)

    def on_nav_left(self):
        self.ids.carousel.load_previous()

    def on_nav_right(self):
        self.ids.carousel.load_next()

    def _check_load_screen(self, slide_screen):
        # checks the current slide if we need to build the dashboard
        # screen on the spot
        if len(slide_screen.children) == 0:
            # if the current screen has no children build and add the screen
            index = self.ids.carousel.index
            # call the builder to actually build the screen
            view = self._view_builders.items()[index][1]()
            slide_screen.add_widget(view)
            view.on_enter()

    def on_current_slide(self, slide_screen):
        if self._initialized == True:
            self._check_load_screen(slide_screen)
            view = slide_screen.children[0]
            self._settings.userPrefs.set_pref('preferences', 'last_dash_screen', view.name)

    def _show_screen(self, screen_name):
        # Find the index of the screen based on the screen name
        # and use that to select the index of the carousel
        carousel = self.ids.carousel
        for i, key in enumerate(self._view_builders.keys()):
            if key == screen_name:
                carousel.index = i
                self._check_load_screen(carousel.current_slide)


    def _show_last_view(self):
        last_screen_name = self._settings.userPrefs.get_pref('preferences', 'last_dash_screen')
        Clock.schedule_once(lambda dt: self._show_screen(last_screen_name))
