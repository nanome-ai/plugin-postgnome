import os
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement, ValueDisplayType
from ..menus import ResourceConfigurationMenu
MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "Resources.json")

class ResourcesMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.config = ResourceConfigurationMenu(plugin, settings)
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 3

        self.lst_resources = self.menu.root.find_node('Resources List').get_content()
        self.edit_variables = self.menu.root.find_node('Edit Variables').get_content()
        self.edit_variables.register_pressed_callback(self.plugin.variables_menu.open_menu)
        self.btn_add_resource = self.menu.root.find_node('Add Resource').get_content()
        self.btn_add_resource.register_pressed_callback(partial(self.add_resource, 'get'))

        self.resource_elements = {}

    def open_menu(self):
        self.refresh_resources()
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)

    def delete_resource(self, resource, list_element):
        return self.settings.delete_resource(resource)

    def rename_resource(self, resource, element, new_name):
        if self.settings.rename_resource(resource, new_name):
            if self.plugin.make_request.request:
                if resource['references'].get(self.plugin.make_request.request.get('id')):
                    self.plugin.make_request.show_request()
            return True
        return False

    def change_resource(self, resource, list_element, new_url):
        if resource and resource['references'] is not None:
            if self.settings.change_resource(resource, new_url=new_url):
                self.config.refresh_resource_url()
                if self.plugin.make_request.request:
                    if resource['references'].get(self.plugin.make_request.request.get('id')):
                        self.plugin.make_request.show_request()
                return True
        return False

    def add_resource(self, method, button = None):
        name = f'Resource {len(self.settings.resource_ids)+1}'
        resource = self.settings.add_resource(name, '', method)
        delete = partial(self.delete_resource, resource)
        open_config = partial(self.config.open_menu, resource)
        el = ListElement(
            self.plugin,
            self.lst_resources,
            name,
            '',
            self.settings.resources,
            ValueDisplayType.Mutable,
            False,
            None,
            deleted=delete,
            renamed=partial(self.rename_resource, resource),
            revalued=partial(self.change_resource, resource),
            config_opened=open_config
        )
        self.lst_resources.items.append(el)
        self.resource_elements[resource['id']] = el
        self.plugin.update_content(self.lst_resources)

    def refresh_resources(self):
        self.lst_resources.items = []
        self.resource_elements = {}
        for r_id, resource in self.settings.resources.items():
            name = resource['name']
            el = ListElement(
                self.plugin,
                self.lst_resources,
                name,
                self.settings.get_resource_item(resource, 'url'),
                None,
                ValueDisplayType.Mutable,
                False,
                self.config,
                deleted=partial(self.delete_resource, resource),
                renamed=partial(self.rename_resource, resource),
                revalued=partial(self.change_resource, resource),
                config_opened=partial(self.config.open_menu, resource)
            )
            self.resource_elements[resource['id']] = el
            self.lst_resources.items.append(el)

    def refresh_resource_name(self, resource):
        el = self.resource_elements.get(resource['id'])
        if el: el.update_name(resource['name'])

    def refresh_resource_url(self, resource):
        el = self.resource_elements.get(resource['id'])
        if el: el.update_value(self.settings.get_resource_item(resource, 'url'))