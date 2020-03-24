import re
import os
import requests
import tempfile
from functools import partial, reduce

from rdkit import Chem
from rdkit.Chem import AllChem

import json
import xmltodict
import requests
import tempfile
import traceback

import nanome
from nanome.util import Logs
from nanome.api.structure import Complex

from . import ResourcesMenu
from . import RequestsMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), 'json', 'MakeRequest.json')
class MakeRequestMenu():
    def __init__(self, plugin, settings, show_all_requests=True):
        self.session = requests.Session()
        self.proxies = {
            'no': 'pass'
        }
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 0
        self.plugin = plugin
        self.settings = settings
        self.variables = None, [None, None]
        self.fields = {}

        self.request = None
        self.tempdir = tempfile.TemporaryDirectory()

        self.__ln_fields = self.menu.root.find_node('Fields')
        self.ln_all_requests = self.menu.root.find_node('All Requests')
        self.ln_all_requests.get_content().register_pressed_callback(lambda b: self.plugin.requests.open_menu())
        self.ln_all_requests.enabled = show_all_requests
        self.btn_load = self.menu.root.find_node('Load Button').get_content()
        self.btn_load.register_pressed_callback(self.load_request)

        self.host = os.environ.get("HOSTNAME", None)

    def open_menu(self):
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)
    
    def set_request(self, request):
        self.request = request
        self.show_request()

    def show_request(self):
        self.__ln_fields.clear_children()
        if not self.request:
            self.plugin.update_menu(self.menu)
            return

        self.variables = self.settings.get_inputs(self.request)
        self.fields = {name:self.fields.get(name, '') for (name, value) in self.variables.values()}
        for var_uid, (var_name, default_value) in self.variables.items():
            field_value = self.fields[var_name]
            ln = nanome.ui.LayoutNode()
            ln.sizing_type = nanome.util.enums.SizingTypes.ratio
            ln.sizing_value = 0.25
            ln.layout_orientation = nanome.util.enums.LayoutTypes.horizontal
            ln.set_padding(top=0.01, down=0.01, left=0.01, right=0.01)

            ln_label = ln.create_child_node()
            label = ln_label.add_new_label(var_name+':')
            label.text_max_size = 0.4
            label.text_vertical_align = nanome.util.enums.VertAlignOptions.Middle

            ln_field = ln.create_child_node()
            ln_field.forward_dist = 0.02
            ln_field.set_padding(top=0.01, down=0.01, left=0.01, right=0.01)
            text_input = ln_field.add_new_text_input()
            text_input.max_length = 0
            text_input.input_text = field_value
            text_input.placeholder_text = default_value
            text_input.max_length = 64
            text_input.register_changed_callback(partial(self.field_changed, var_name))
            text_input.register_submitted_callback(partial(self.clean_field, var_name, True))
            self.__ln_fields.add_child(ln)
        self.__ln_fields.create_child_node()
        self.plugin.update_menu(self.menu)

    def field_changed(self, var_name, text_input):
        self.fields[var_name] = text_input.input_text

    def clean_field(self, name, update=False, text_input=None):
        pass
        # value = text_input.input_text if (text_input and text_input.input_text) else self.fields[name]
        # if value:
        #     self.settings.set_variable(name, value)
        #     self.plugin.update_node(self.__ln_fields)

    def set_load_enabled(self, enabled):
        self.btn_load.unusable = not enabled
        self.plugin.update_content(self.btn_load)

    def contextualize(self, variable, contexts, left_wrapper="", right_wrapper=""):
        cvar = self.settings.contextualize(variable, contexts, add_to_context=True, default_value="", left_wrapper=left_wrapper, right_wrapper=right_wrapper)
        return cvar

    def convert_to_json_string(self, response_text, response_type):
        if 'json' in response_type:
            coerced_response = response_text
        elif 'xml' in response_type:
            coerced_response = json.dumps(xmltodict.parse(response_text))
        elif 'text' in response_type:
            coerced_response = '{"root": '+ response_text + '}'
        return coerced_response

    def get_response(self, resource, contexts, data=None):
        """ Responsible for getting a response from a resource.
            As this method calls settings.set_output,
            It gives a response decontextualized from the resource's inputs
            and will update the resource's output variables in the process.
        """
        load_url = self.contextualize(variable=resource['url'], contexts=contexts)
        if self.host: load_url = load_url.replace('localhost', self.host)
        method = resource['method'].lower()
        headers = dict(resource['headers'].values())
        headers = {self.contextualize(name, contexts):self.contextualize(value, contexts) for name,value in headers.items()}
        data = self.contextualize(data or resource['data'], contexts=contexts)
        if method == 'post':
            headers.update({'Content-Length': str(len(data))})
        elif headers.get('Content-Length'):
            del headers['Content-Length']

        try:
            Logs.debug(f"load url: {load_url}")
            if method == 'get':
                response = self.session.get(load_url, headers=headers, proxies=self.proxies, verify=False)
            elif method == 'post':
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'text/plain'
                response = self.session.post(load_url, data=json.loads(data), proxies=self.proxies, verify=False)
            
            json_text = self.convert_to_json_string(response.text, response.headers.get('Content-Type', 'text/plain'))
            response._content = bytes(json_text, 'utf-8')
            self.settings.set_output(resource, response.text, dict(response.headers))
        except:
            exception = self.get_exception("An error occured while making the request")
            Logs.debug(traceback.format_exc())
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"{exception}")
            return None

        return response
    
    def save_fields_to_vars(self):
        for name, value in self.fields.items():
            if value:
                self.settings.set_variable(None, name, value)

    def load_request(self, button=None):
        if not self.request:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.message, "Please select a request")
            return

        self.save_fields_to_vars()

        self.set_load_enabled(False)
        results = {}
        for i, step in enumerate(self.request['steps']):
            resource = self.settings.get_resource(step['resource'])
            import_type = resource['import type']
            metadata = step['metadata_source']
            data = resource['data'].replace("\'", "\"")
            # override data if necessary
            data_override_field_name = f"{self.request['name']} {step['name']} data"
            if step['override_data']:
                data = self.fields[data_override_field_name]

            contexts = [self.fields, results, self.settings.variables]
            response = self.get_response(resource, contexts, data)
            var_uid, var_value = self.settings.get_output_variable(resource, 0)
            if not response:
                self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"Step {i} failed. Aborting {self.request['name']}")
                self.set_load_enabled(True)
                return
            results[f'step{i+1}'] = json.dumps(var_value) or response.text
            Logs.debug(f'setting step{i+1} to {var_value} ({self.settings.variables[var_uid][0]})')
            if import_type:
                import_name = self.contextualize(variable=resource['import name'], contexts=contexts)
                self.import_to_nanome(import_name, import_type, var_value or response.text, metadata)
        self.set_load_enabled(True)

    def import_to_nanome(self, name, filetype, contents, metadata):
        try:
            file_path = os.path.join(self.tempdir.name, name+filetype)
            with open(file_path, 'w+') as file:
                file.write(contents)
                file.seek(0)
                if filetype == ".pdb":
                    complex = nanome.structure.Complex.io.from_pdb(path=file.name)
                    self.plugin.add_bonds([complex], partial(self.bonds_ready, name, metadata))
                elif filetype == ".sdf":
                    complex = nanome.structure.Complex.io.from_sdf(path=file.name)
                    self.bonds_ready(name, metadata, [complex])
                elif filetype == ".cif":
                    complex = nanome.structure.Complex.io.from_mmcif(path=file.name)
                    self.plugin.add_bonds([complex], partial(self.bonds_ready, name, metadata))
                elif filetype == ".mol":
                    self.plugin.send_files_to_load([file.name])
                    # self.plugin.add_bonds([complex], partial(self.bonds_ready, name, metadata))
                elif filetype == ".smi":
                    complex = self.complexFromSMILES(contents)
                    self.plugin.add_bonds([complex], partial(self.bonds_ready, name, metadata))
                elif filetype == '.pdf':
                    self.plugin.send_files_to_load([file])
                    return
                elif filetype == '.nanome':
                    self.plugin.send_files_to_load([file])
                    return
                    # load workspace
                elif filetype == ".json":
                    complex = nanome.structure.Complex()
                    self.bonds_ready(name, metadata, [complex])
                else:
                    Logs.error("Unknown filetype")
        except: # Making sure temp file gets deleted in case of problem
            self._loading = False
            exception = self.get_exception("Error while parsing")
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"Import failure. Have you configured the resource for {filetype} files?")

    def complexFromSMILES(self, smiles):
        mol = Chem.MolFromSmiles(smiles)
        AllChem.Compute2DCoords(mol)
        with tempfile.TemporaryFile(mode='w+') as temp:
            w = Chem.SDWriter(temp)
            w.write(mol)
            w.flush()
            temp.seek(0)
            return Complex.io.from_sdf(file=temp)

    def get_remarks(self, obj):
        dict_found = False
        for value in obj.values():
            if type(value) is dict:
                if not dict_found or len(value) > len(obj):
                    obj = self.get_remarks(value)
                dict_found = True
        return obj

    def bonds_ready(self, name, metadata, complex_list):
        if len(complex_list):
            try:
                if metadata: complex_list[0]._remarks.update(self.get_remarks(json.loads(metadata)))
            except Exception as e:
                self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"Metadata error. Have you configured the resource for metadata json?")
            self.plugin.add_dssp(complex_list, partial(self.complex_ready, name))

    def complex_ready(self, name, complex_list):
        self._loading = False
        self.plugin.send_notification(nanome.util.enums.NotificationTypes.success, f"Successfully loaded while parsing metadata")
        complex_list[0].molecular.name = name
        self.plugin.add_to_workspace(complex_list)

    def get_exception(self, default_error, pattern=".*?([\w ]*Error:[\w ]*)"):
        exc = traceback.format_exc()
        Logs.debug(exc)
        exc_lines = re.findall(pattern, exc, re.MULTILINE)
        if not len(exc_lines) or len(exc_lines[0]) < 15:
            return default_error
        else:
            return exc_lines[0]

class Response:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)