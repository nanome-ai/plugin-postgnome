import os
import requests
from requests.exceptions import HTTPError
import json
from collections import OrderedDict
import xmltodict
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement

MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "ResponseConfig.json")
RESPONSE_SETUP = os.path.join(os.path.dirname(__file__), "json", "MakeRequest.json")

class ResponseConfigurationMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 5
        self.response_setup = nanome.ui.Menu(6, 'Response Setup')
        self.variable_confirm = nanome.ui.Menu(7, 'Confirm Variable Creation')

        self.resource = None
        self.response = None

        self.lst_response_elements = self.menu.root.find_node("Response Entry List").get_content()
        self.btn_refresh = self.menu.root.find_node("Refresh Button").get_content()
        self.btn_refresh.register_pressed_callback(self.refresh_response)

    def open_menu(self, resource=None):
        self.set_resource(resource)

    def refresh_response(self, button=None):
      self.settings.clear_output(self.resource)
      self.response = None
      self.menu.enabled = False
      self.plugin.update_menu(self.menu)
      self.setup_variable_config()

    # def response_to_json(self, response):
      

    def set_resource(self, resource):
      self.response = None
      self.resource = resource
      if self.resource['output'] and self.resource['output variables']:
        self.response = Response(text=self.resource['output'], headers=self.resource['output headers'])
        self.show_hierarchy()
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)
      else:
        self.setup_variable_config()

    def get_and_set_response(self):
      try:
        if not self.response:
          response = self.plugin.make_request.get_response(self.resource, [self.settings.variables])
          if response:
            response.raise_for_status()
            self.response = Response(text=response.text, headers=response.headers, status_code=response.status_code)
          return response
      except HTTPError as http_err:
        Logs.debug(response.text)
        self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"{response.text}")
        return None

    def show_hierarchy(self, button=None):
      # Logs.debug('showing...')
      self.lst_response_elements.items = []
      self.get_and_set_response()
      response_object = self.settings.get_response_object(self.resource)
      # Logs.debug(f'response object is {response_object}')
      if not response_object:
        response_type = self.settings.get_response_type(self.resource)
        self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"{response_type} content not supported")

      self.response_setup.enabled = False
      self.plugin.update_menu(self.response_setup)

      self.draw_elements(response_object)
      self.menu.enabled = True
      self.plugin.update_menu(self.menu)
      
    def draw_elements(self, obj, path=[]):
      inputs = self.settings.get_inputs(self.resource)
      outputs = {uid:self.settings.variables[uid] for uid in self.resource['output variables'].keys()}
      Logs.debug(outputs)
      decontexti =   [{inp_v: [inp_n] for inp_id, [inp_n, inp_v] in inputs.items()}]
      decontextu = [{inp_v: [inp_id] for inp_id, [inp_n, inp_v] in inputs.items()}]
      decontexto = [{inp_v: [inp_n] for inp_id, [inp_n, inp_v] in outputs.items()}]
      if type(obj) is dict:
        for key, value in obj.items():
          name_key = self.settings.decontextualize_string(key, decontexti, left_wrapper='{{', right_wrapper='}}')
          uid_key = self.settings.decontextualize_string(key, decontextu, left_wrapper='{{', right_wrapper='}}')
          if type(value) is str:
            value = self.settings.decontextualize_string(value, decontexto, left_wrapper='{{', right_wrapper='}}')
          Logs.debug(f"key:{key}, name_key:{name_key}")
          self.create_button(name_key, path, name_key!=key)
          self.draw_elements(value, path+[uid_key])
      elif type(obj) is list:
        for i, value in enumerate(obj):
          self.create_button(str(i), path)
          self.draw_elements(value, path+[str(i)])
      else:
        self.create_button(str(obj), path)

    def create_button(self, text, json_path=None, disabled=False):
      ln = nanome.ui.LayoutNode()
      ln.set_padding(left=(len(json_path))*0.1)
      btn = ln.add_new_button(text)
      btn.name = text
      btn.json_path = json_path
      btn.text.horizontal_align = btn.HorizAlignOptions.Middle
      btn.register_pressed_callback(self.open_variable_setup)
      btn.unusable = disabled
      self.lst_response_elements.items.append(ln)

    def open_variable_setup(self, button):
      self.variable_confirm.root.clear_children()

      self.variable_confirm.var_path = button.json_path
      self.variable_confirm.var_value = button.name

      self.variable_confirm.height = 1
      self.variable_confirm.width = 1

      ln_name = self.variable_confirm.root.create_child_node()
      ln_name.sizing_type = ln_name.SizingTypes.ratio
      ln_name.sizing_value = 0.2

      ln_name.create_child_node().add_new_label('Name').text_horizontal_align = nanome.util.enums.HorizAlignOptions.Middle
      ln_var_name = ln_name.create_child_node()
      ln_var_name.forward_dist = 0.02
      inp_var_name = ln_var_name.add_new_text_input()
      inp_var_name.placeholder_text = 'variable name'
      inp_var_name.max_length = 0
      inp_var_name.max_length = 24
      inp_var_name.register_changed_callback(self.set_output_variable)

      ln_value = self.variable_confirm.root.create_child_node()
      ln_value.sizing_type = ln_name.SizingTypes.ratio
      ln_value.sizing_value = 0.7

      ln_label = ln_value.create_child_node()
      ln_label.sizing_type = ln_name.SizingTypes.ratio
      ln_label.sizing_value = 0.1
      ln_label.forward_dist = 0.02
      ln_label.add_new_label('Value').text_horizontal_align = nanome.util.enums.HorizAlignOptions.Middle

      ln_var_value = ln_value.create_child_node()
      ln_var_value.sizing_type = ln_var_value.SizingTypes.ratio
      ln_var_value.sizing_value = 0.5

      ln_var_value.add_new_label(text=button.text.value.idle)

      ln_create_var = self.variable_confirm.root.create_child_node()
      ln_create_var.sizing_type = ln_create_var.SizingTypes.ratio
      ln_create_var.sizing_value = 0.1

      btn_create = ln_create_var.add_new_button(text="Set Resource Variable")
      btn_create.register_pressed_callback(self.create_output_var)

      self.variable_confirm.enabled = True
      self.plugin.update_menu(self.variable_confirm)

      Logs.debug(f'Are you sure you want to create a variable for {button.name}?')
      Logs.debug(f'variable path: {button.json_path}')

    def setup_variable_config(self):
      Logs.debug("testing...")
      self.response_setup.root.clear_children()
      ln = self.response_setup.root.create_child_node()
      ln.sizing_type = ln.SizingTypes.ratio
      ln.sizing_value = 0.9
      ln.forward_dist = 0.002
      ls = ln.add_new_list()
      pfb = nanome.ui.LayoutNode()
      pfb.layout_orientation = pfb.LayoutTypes.horizontal
      pfb.lbl = pfb.create_child_node().add_new_label('Label')
      ln_inp = pfb.create_child_node()
      ln_inp.forward_dist = 0.002
      pfb.inp = ln_inp.add_new_text_input()
      pfb.inp.placeholder_text = "test value"

      for uid, (name, value) in self.settings.get_inputs(self.resource).items():
        print(f"variable: {name}, value: {value}")
        pfb_var = pfb.clone()
        children = pfb_var.get_children()
        lbl, inp = children[0].get_content(), children[1].get_content()
        lbl.text_value = name
        inp.max_length = 0
        inp.input_text = value
        inp.register_changed_callback(partial(self.var_changed, uid))
        ls.items.append(pfb_var)
        pfb_var.forward_dist = 0.02
      if len(ls.items) == 0:
        self.response_setup.root.clear_children()
        self.response_setup.root.create_child_node().add_new_label('(Resource does not require parameters)')
      
      btn = self.response_setup.root.create_child_node().add_new_button('Show Response')
      btn.register_pressed_callback(self.show_hierarchy)
      self.response_setup.enabled = True
      self.plugin.update_menu(self.response_setup)

    def var_changed(self, uid, text_input):
      self.settings.set_variable(uid, None, text_input.input_text)

    def set_output_variable(self, text_input):
      self.variable_confirm.var_name = text_input.input_text

    def create_output_var(self, button):
      out_var_names = list(self.resource['output variables'].keys())
      var_name = self.variable_confirm.var_name
      var_path = self.variable_confirm.var_path
      var_value = self.variable_confirm.var_value
      self.settings.set_output_variable(self.resource, None, var_name, var_path, var_value)
      decontextualized_output = self.settings.decontextualize_output(self.resource, json.loads(self.response.text))
    
      # close variable confirm menu
      self.variable_confirm.enabled = False
      self.plugin.update_menu(self.variable_confirm)
      # redisplay the hierarchy with decontextualized output
      self.show_hierarchy()
      self.menu.enabled = True
      self.plugin.update_menu(self.menu)

      self.plugin.send_notification(nanome.util.enums.NotificationTypes.success, "{{"+var_name+"}}" + f' now defined by response from resource: {self.resource["name"]}')

class Response:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)