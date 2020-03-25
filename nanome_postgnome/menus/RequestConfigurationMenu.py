import os
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement, ValueDisplayType
from ..menus import ResourceConfigurationMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "RequestConfig.json")

class RequestConfigurationMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.resource_config = ResourceConfigurationMenu(plugin, settings)
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 2

        self.request = None
        self.resource = None

        self.step_i = 1

        self.lst_steps = self.menu.root.find_node('Step List').get_content()
        self.lst_all_steps = self.menu.root.find_node('All Steps List').get_content()
        self.btn_add_step = self.menu.root.find_node('Add Step').get_content()
        self.btn_add_step.register_pressed_callback(self.add_step)

    def open_menu(self, request):
        self.menu.enabled = True
        self.refresh_resources()
        self.set_request(request)
        self.plugin.update_menu(self.menu)

    def refresh_resources(self):
        self.lst_all_steps.items = []
        if not self.resource and self.settings.resources:
            self.resource = self.settings.get_resource(-1)
        for r_id, resource in self.settings.resources.items():
            name = resource['name']
            pfb = nanome.ui.LayoutNode()
            button = pfb.add_new_button(name)
            button.resource = resource
            button.selected = r_id == self.resource['id']
            button.text_horizontal_align = nanome.util.enums.HorizAlignOptions.Middle
            button.register_pressed_callback(self.set_resource)
            self.lst_all_steps.items.append(pfb)
        self.plugin.update_content(self.lst_all_steps)

    def set_resource(self, button):
        self.resource = button.resource
        for element in self.lst_all_steps.items:
            btn = element.get_content()
            btn.selected = btn.resource['id'] == self.resource['id']
        self.plugin.update_content(self.lst_all_steps)

    def set_request(self, request):
        self.request = request
        self.lst_steps.items = []
        steps = request['steps']
        self.step_i = len(steps) + 1
        for step in steps:
            step_name = step['name']
            resource = self.settings.get_resource(step['resource'])
            external_toggle = partial(self.toggle_use_data_in_request, step)
            open_config = partial(self.config_opened, resource)
            el = ListElement(
                self.plugin,
                self.lst_steps,
                step_name,
                '',
                self.settings.resources,
                ValueDisplayType.Mutable,
                resource['method'] == 'post',
                self.menu,
                deleted=self.delete_step,
                renamed=partial(self.rename_step, step),
                revalued=partial(self.validate_new_resource, step),
                external_toggle=external_toggle,
                config_opened=open_config
            )
            el.set_top_panel_text(resource['name'])
            el.set_resource_placeholder("Metadata source ({{step1}})")
            el.set_tooltip('Override post data during request')
            self.lst_steps.items.append(el)
            name = request['name']
            self.menu.title = f"{name} {'Configuration' if len(name) < 16 else 'Config'}"
            self.plugin.update_menu(self.menu)

    def add_step(self, button):
        step_name = f'Step {self.step_i}'
        self.step_i += 1
        if not len(self.settings.resource_ids):
            self.settings.add_resource()
        
        resource = self.resource or self.settings.get_resource(-1) or {}
        resource_id = resource.get('id', '')
        step = self.settings.add_step(self.request['id'], step_name, resource_id, '', False)
        if not step:
            return
        external_toggle = partial(self.toggle_use_data_in_request, step)
        open_config = partial(self.config_opened, resource)
        close_config = partial(self.config_closed, resource)
        el = ListElement(
            self.plugin,
            self.lst_steps,
            step_name,
            '',
            self.settings.resources,
            ValueDisplayType.Mutable,
            resource['method'] == 'post',
            self.menu,
            deleted=self.delete_step,
            renamed=partial(self.rename_step, step),
            revalued=partial(self.validate_new_resource, step),
            external_toggle=external_toggle,
            config_opened=open_config,
            config_closed=close_config
        )
        el.set_top_panel_text(resource.get('name', ''))
        el.set_resource_placeholder('Metadata source ({{step1}})')
        el.set_tooltip('Override post data during request')
        self.lst_steps.items.append(el)
        self.plugin.update_content(self.lst_steps)

    def delete_step(self, element):
        index = self.lst_steps.items.index(element)
        return self.settings.delete_step(self.request['id'], index)

    def rename_step(self, step, element, new_name):
        return self.settings.rename_step(self.request['id'], step, new_name)

    def validate_new_resource(self, step, list_element, metadata_source_name):
        step_index = self.plugin.make_request.request['steps'].index(step)
        if metadata_source_name in self.settings.variables:
            step['metadata_source'] = metadata_source_name
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.success, "Resource for step updated")
            return True
        else:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Resource does not exist")
            return False

    def config_opened(self, resource):
        self.resource_config.open_menu(resource)

    def config_closed(self, resource):
        pass

    def toggle_use_data_in_request(self, step, element, use_data):
        step['override_data'] = not step['override_data']
        self.plugin.make_request.show_request()
        return True

    def refresh_steps(self):
        if self.request:
            self.set_request(self.request)
            self.plugin.update_content(self.lst_steps)