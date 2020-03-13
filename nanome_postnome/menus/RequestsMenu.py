import os
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement
from ..menus.RequestConfigurationMenu import RequestConfigurationMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "Requests.json")

class RequestsMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 1
        self.config = RequestConfigurationMenu(self.plugin, self.settings)

        self.req_i = 0

        self.requests_list = self.menu.root.find_node("Requests").get_content()
        self.btn_new_request = self.menu.root.find_node("New Request").get_content()
        self.btn_new_request.register_pressed_callback(self.add_request)

    def open_menu(self):
        self.refresh_requests()
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)

    def add_request(self, button):
        name = f'Request {self.req_i}'
        request = self.settings.add_request(name)
        self.req_i += 1
        element = ListElement(
            self.plugin,
            self.requests_list,
            name,
            externally_used=True,
            config=self.config,
            deleted=self.delete_request,
            renamed=partial(self.request_renamed, request),
            external_toggle=self.set_active_request,
            config_opened=partial(self.config.open_menu, request)
        )
        element.r_id = request['id']
        element.set_tooltip("Set to active request")
        self.requests_list.items.append(element)
        self.plugin.update_content(self.requests_list)

    def delete_request(self, element):
        request = self.settings.requests.get(element.r_id)
        if self.plugin.make_request.request is request:
            self.plugin.make_request.request = None
            self.plugin.make_request.show_request()
        return self.settings.delete_request(element.r_id)

    def request_renamed(self, request, element, new_name):
        return self.settings.rename_request(request, new_name)

    def set_active_request(self, list_element, toggled):
        for item in self.requests_list.items:
                item.set_use_externally(item is list_element and not toggled, update=False)
        self.plugin.make_request.set_request(self.settings.requests[list_element.r_id] if toggled else None)
        return True

    def refresh_requests(self):
        self.requests_list.items = []
        for r_id, request in self.settings.requests.items():
            name = request['name']
            element = ListElement(
            self.plugin,
            self.requests_list,
            name,
            externally_used=True,
            config=self.config,
            deleted=self.delete_request,
            renamed=partial(self.request_renamed, request),
            external_toggle=self.set_active_request,
            config_opened=partial(self.config.open_menu, request)
            )
            element.r_id = r_id
            element.set_tooltip("Set to active request")
            if request['id'] is self.plugin.make_request.request['id']:
                element.set_use_externally(True)
            self.requests_list.items.append(element)