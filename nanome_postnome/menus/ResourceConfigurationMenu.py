import os
import re
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement
from . import ResponseConfigurationMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "ResourceConfig.json")

class ResourceConfigurationMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.response_config = ResponseConfigurationMenu(plugin, settings)
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 4

        self.resource = None
        self.step_elements = []

        self.headers_i = 1

        self.inp_resource_url = self.menu.root.find_node('URL Input').get_content()
        self.inp_resource_url.register_changed_callback(self.resource_url_changed)
        self.ls_request_types = self.menu.root.find_node('Request Methods').get_content()
        self.pfb_header = self.menu.root.find_node('Header Prefab')
        self.ls_headers = self.menu.root.find_node('Headers List').get_content()
        self.inp_post_data = self.menu.root.find_node('Data Input').get_content()
        self.inp_post_data.register_changed_callback(self.data_changed)
        self.inp_import_content = self.menu.root.find_node('Import Content Input').get_content()
        self.inp_import_content.register_changed_callback(self.import_content_changed)
        self.inp_import_name = self.menu.root.find_node('Import Name Input').get_content()
        self.inp_import_name.register_changed_callback(self.import_name_changed)
        self.ls_import_types = self.menu.root.find_node('Import Type List').get_content()
        self.btn_response_config = self.menu.root.find_node('Configure Button').get_content()
        self.btn_response_config.register_pressed_callback(self.open_response_config)
        self.prepare_menu()

    def open_menu(self, resource):
        self.menu.enabled = True
        self.set_resource(resource)
        self.plugin.update_menu(self.menu)

    def open_response_config(self, button):
        self.response_config.open_menu(self.resource)

    def prepare_menu(self):
        for method in ['get', 'post']:
            ln = nanome.ui.LayoutNode()
            ln.name = method
            btn = ln.add_new_button(method)
            btn.register_pressed_callback(self.set_resource_method)
            self.ls_request_types.items.append(ln)

        for import_type in ['.pdb', '.cif', '.sdf', '.mol', '.smi', '.pdf', '.nanome', '.json']:
            ln = nanome.ui.LayoutNode()
            ln.name = import_type
            btn = ln.add_new_button(import_type)
            btn.register_pressed_callback(self.set_resource_import_type)
            self.ls_import_types.items.append(ln)

    def set_resource(self, resource):
        self.resource = resource
        self.inp_resource_url.input_text = resource['url']
        self.inp_import_name.input_text = resource['import name']
        self.update_request_type()
        self.set_headers(resource['headers'])
        self.update_import_type()
        self.inp_post_data.input_text = resource['data']

    def refresh_resource_url(self):
        self.inp_resource_url.input_text = self.resource['url']
        self.plugin.update_content(self.inp_resource_url)

    def resource_url_changed(self, text_input):
        self.settings.change_resource(self.resource, new_url=text_input.input_text)
        self.plugin.resources_menu.refresh_resource_url(self.resource)
        self.update_other_menus()

    def data_changed(self, text_input):
        self.settings.change_resource(self.resource, new_data=text_input.input_text)
        self.update_other_menus()

    def import_content_changed(self, text_input):
        self.settings.change_resource(self.resource, new_import_content=text_input.input_text)
        self.update_other_menus()

    def import_name_changed(self, text_input):
        self.settings.change_resource(self.resource, new_import_name=text_input.input_text)
        self.update_other_menus()

    def update_other_menus(self):
        if self.plugin.make_request.request:
            if self.resource['references'].get(self.plugin.make_request.request['id']):
                self.plugin.make_request.show_request()

    def add_step_dependency(self, step_element, reset=False):
        if reset:
            self.steps = []
        self.step_elements.append(step_element)

    def update_request_type(self):
        for ln_method in self.ls_request_types.items:
            btn = ln_method.get_content()
            btn.selected = ln_method.name == self.resource['method']
        self.plugin.update_content(self.ls_request_types)

    def update_import_type(self):
        for ln_import_type in self.ls_import_types.items:
            btn = ln_import_type.get_content()
            btn.selected = ln_import_type.name == self.resource['import type']
        self.plugin.update_content(self.ls_import_types)

    def set_headers(self, headers):
        self.ls_headers.items = []
        for (h_id, (name, value)) in headers.items():
            pfb = self.header_prefab(h_id, name, value)
            self.ls_headers.items.append(pfb)
        ln_new_header = nanome.ui.LayoutNode()
        btn = ln_new_header.add_new_button('New Header')
        btn.register_pressed_callback(self.new_header)
        self.ls_headers.items.append(ln_new_header)

    def header_prefab(self, header_id, name, value):
        pfb = self.pfb_header.clone()
        ln_delete = pfb.find_node('Delete')
        ln_delete.get_content().element = pfb
        name_input = pfb.find_node('Name').get_content()
        value_input = pfb.find_node('Value').get_content()
        name_input.input_text = name
        value_input.input_text = value
        name_input.register_changed_callback(partial(self.set_header, header_id, name_input, value_input))
        value_input.register_changed_callback(partial(self.set_header, header_id, name_input, value_input))
        ln_delete.get_content().register_pressed_callback(partial(self.delete_header, header_id))
        return pfb

    def new_header(self, button):
        self.headers_i += 1
        header_name = f"Header {self.headers_i}"
        header_id = self.settings.add_header(self.resource, header_name, '')
        if header_id:
            pfb = self.header_prefab(header_id, header_name, '')
            self.ls_headers.items.insert(len(self.ls_headers.items)-1, pfb)
            self.plugin.update_content(self.ls_headers)

    def set_header(self, header_id, name_input, value_input, text_input):
        if name_input.input_text and value_input.input_text:
            self.settings.set_header(self.resource, header_id, name_input.input_text, value_input.input_text)

    def delete_header(self, header_id, button):
        if self.settings.delete_header(self.resource, header_id):
            self.ls_headers.items.remove(button.element)
            self.plugin.update_content(self.ls_headers)

    def set_resource_method(self, button=None):
        if self.resource:
            if self.resource['method'] != button.text.value.idle:
                self.settings.set_output(self.resource, output="", output_headers={}, override=True)
                self.resource['method'] = button.text.value.idle
                self.update_request_type()
                self.plugin.update_content(button)
        else:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Resource undefined")

    def set_resource_import_type(self, button=None):
        if self.resource:
            self.resource['import type'] = button.text.value.idle if not button.selected else None
            self.update_import_type()
            self.plugin.update_content(button)
        else:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Resource undefined")