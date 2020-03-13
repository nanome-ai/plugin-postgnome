import nanome
from nanome.util import Logs
from functools import partial

from ..components import ListElement, ValueDisplayType

class VariablesMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings

        self.menu = nanome.ui.Menu(8, 'All Variables')

        self.var_i = 0

        self.ln_list = self.menu.root.create_child_node()
        self.ln_btn  = self.menu.root.create_child_node()
        self.setup_menu()
        
    def setup_menu(self):
        ln_list = self.ln_list
        ln_list.sizing_type = ln_list.SizingTypes.ratio
        ln_list.sizing_value = 0.7
        ln_list.forward_dist = 0.02
        self.lst_vars = ln_list.add_new_list()
        self.lst_vars.display_rows = 4

        ln_btn = self.ln_btn
        ln_btn.sizing_type = ln_btn.SizingTypes.ratio
        ln_btn.sizing_value = 0.1
        ln_btn.forward_dist = 0.02
        btn = ln_btn.add_new_button('Create Variable')
        btn.register_pressed_callback(self.create_variable)

    def open_menu(self, button=None):
        self.refresh_vars()
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)

    def new_variable_name(self):
        self.var_i += 1
        return f'variable {self.var_i}'

    def refresh_vars(self):
        self.lst_vars.items = []
        for var_id, (var_name, var_value) in self.settings.variables.items():
            el = ListElement(
                self.plugin,
                self.lst_vars,
                var_name,
                var_value,
                None,
                ValueDisplayType.Mutable,
                False,
                None,
                deleted=self.delete_variable,
                renamed=self.rename_variable,
                revalued=self.change_variable_value,
            )
            el.var_id = var_id
            el.set_resource_placeholder("variable value")
            el.set_renameable(False)
            el.set_configurable(False)
            self.lst_vars.items.append(el)
        self.plugin.update_content(self.lst_vars)

    def create_variable(self, text_input):
        var_name = self.new_variable_name()
        var_id = self.settings.touch_variable(var_name)
        delete = partial(self.delete_variable)
        el = ListElement(
            self.plugin,
            self.lst_vars,
            var_name,
            '',
            None,
            ValueDisplayType.Mutable,
            False,
            None,
            deleted=delete,
            renamed=self.rename_variable,
            revalued=self.change_variable_value,
        )
        el.var_id = var_id
        el.set_renameable(False)
        el.set_configurable(False)
        self.lst_vars.items.append(el)
        self.plugin.update_content(self.lst_vars)

    def rename_variable(self, list_element, text_input):
        self.settings.set_variable(list_element.var_id, text_input.input_text)
        Logs.debug("variable is now...")
        Logs.debug(self.settings.get_variable_by_id(list_element.var_id))
        return True
    
    def change_variable_value(self, list_element, new_value):
        self.settings.set_variable(list_element.var_id, None, new_value)
        Logs.debug("variable is now...")
        Logs.debug(self.settings.get_variable_by_id(list_element.var_id))
        return True

    def delete_variable(self, list_element):
        self.settings.delete_variable_by_id(list_element.var_id)
        return True