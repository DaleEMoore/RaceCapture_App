import kivy
kivy.require('1.8.0')
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.app import Builder

Builder.load_file('toolbarview.kv')

class ToolbarView(BoxLayout):

    def __init__(self, **kwargs):
        self.register_event_type('on_read_config')
        self.register_event_type('on_write_config')
        super(ToolbarView, self).__init__(**kwargs)
        self.rcp = kwargs.get('rcp', None)
        self.app = kwargs.get('app', None)

    def on_read_config(self, instance, *args):
        pass
    
    def on_write_config(self, instance, *args):
        pass
    
    def readConfig(self):
        self.dispatch('on_read_config', None)

    def writeConfig(self):
        self.dispatch('on_write_config', None)

class ToolbarButton(Button):
    pass
