#
# Race Capture App
#
# Copyright (C) 2014-2016 Autosport Labs
#
# This file is part of the Race Capture App
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details. You should
# have received a copy of the GNU General Public License along with
# this code. If not, see <http://www.gnu.org/licenses/>.

import kivy
kivy.require('1.9.1')
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.app import Builder
from autosportlabs.racecapture.views.dashboard.widgets.gauge import Gauge
from autosportlabs.racecapture.views.dashboard.widgets.imugauge import ImuGauge
from autosportlabs.racecapture.views.dashboard.dashboardscreen import DashboardScreen
from utils import kvFind, kvFindClass
from kivy.clock import Clock
from utils import kvFindClass

COMBO_VIEW_KV = """
<ComboView>:
    BoxLayout:
        orientation: 'horizontal'
        BoxLayout:
            size_hint_x: 0.1
        ImuGauge:
            size_hint_x: 0.8
            rcid: 'imu_gauge'
        BoxLayout:
            size_hint_x: 0.1
"""

class ComboView(DashboardScreen):
    Builder.load_string(COMBO_VIEW_KV)

    def __init__(self, databus, settings, **kwargs):
        super(ComboView, self).__init__(**kwargs)
        self.register_event_type('on_tracks_updated')
        self._databus = databus
        self._settings = settings
        self._initialized = False

    def init_view(self):
        data_bus = self._databus
        settings = self._settings

        gauges = list(kvFindClass(self, Gauge))

        for gauge in gauges:
            gauge.settings = settings
            gauge.data_bus = data_bus
        self._initialized = True

    def on_tracks_updated(self, trackmanager):
        pass

    def on_enter(self):
        if not self._initialized:
            self.init_view()
