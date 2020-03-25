import re
import os
import requests
from functools import partial

import json
import requests
import tempfile
import traceback

import nanome
from nanome.util import Logs

from .Settings import Settings
from .menus.MakeRequestMenu import MakeRequestMenu
from .menus.VariablesMenu import VariablesMenu
from .menus.ResourcesMenu import ResourcesMenu
from .menus.RequestsMenu import RequestsMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), 'json', 'MakeRequest.json')
class Postgnome(nanome.PluginInstance):
    def __init__(self):
        self.session = requests.Session()
        self.proxies = {
            'no': 'pass'
        }
        self.settings = Settings(self)
        self.make_request = MakeRequestMenu(self, self.settings)
        self.variables_menu = VariablesMenu(self, self.settings)
        self.requests = RequestsMenu(self, self.settings)
        self.resources_menu = ResourcesMenu(self, self.settings)

    def start(self):
        self.set_plugin_list_button(self.PluginListButtonType.run, 'Save')
        self.set_plugin_list_button(self.PluginListButtonType.advanced_settings, 'Edit Resources')
        if self.settings.request_ids:
            self.make_request.request = self.settings.get_request(-1)
            self.make_request.show_request()
        self.make_request.open_menu()

    def on_run(self):
        self.make_request.open_menu()
        self.settings.save_settings()

    def on_stop(self):
        self.settings.save_settings()

    def on_advanced_settings(self):
        self.resources_menu.open_menu()

def main():
    plugin = nanome.Plugin('Postgnome', 'A web request plugin for Nanome', 'Loading', True)
    plugin.set_plugin_class(Postgnome)
    plugin.run('127.0.0.1', 8888)

if __name__ == '__main__':
    main()