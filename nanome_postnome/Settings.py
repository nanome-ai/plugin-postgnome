import re
import json
import xmltodict
import os
import uuid
import traceback
from functools import partial, reduce

import nanome
BASE_PATH = os.path.dirname(os.path.realpath(__file__))
MENU_PATH = os.path.join(BASE_PATH, 'menus', 'json', 'Settings.json')
OFF_ICON_PATH = os.path.join(BASE_PATH, 'assets', 'icons', 'off.png')
ON_ICON_PATH = os.path.join(BASE_PATH, 'assets', 'icons', 'on.png')

class Settings():

    def __init__(self, plugin):
        self.plugin = plugin
        self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)

        self.variables = {}
        self.resource_ids = []
        self.resources = {}
        self.request_ids = []
        self.requests = {}
        self.__settings = {}

        self.__settings_path = os.path.normpath(os.path.join(plugin.plugin_files_path, 'postnome', 'settings.json'))
        print(f'settings: {self.__settings_path}')
        if not os.path.exists(os.path.dirname(self.__settings_path)):
            os.makedirs(os.path.dirname(self.__settings_path))
        self.load_settings()

    def generate_settings(self):
        for setting_name in ['variables', 'resource_ids', 'resources', 'request_ids', 'requests']:
            yield setting_name, getattr(self, setting_name)

    def load_settings(self, update=False):
        if os.path.exists(self.__settings_path):
            with open(self.__settings_path, 'r') as settings_file:
                settings = json.load(settings_file)
                for key, value in settings.items():
                    setattr(self, key, value)
        if update:
            self.plugin.update_menu(self.__menu)

    def save_settings(self, menu=None):
        with open(self.__settings_path, 'w') as settings_file:
            json.dump(dict(self.generate_settings()), settings_file)
        self.plugin.send_notification(nanome.util.enums.NotificationTypes.success, "Settings saved.")

    def vars_in_string(self, string):
        fields = set()
        for field in re.findall('{{(.*?)}}', string):
            fields.add(field)
            self.touch_variables([field])
        return fields

    def vars_in_list(self, list):
        fields = set()
        for string in list:
            fields.update(self.vars_in_string(string))
        return fields

    def try_contextualize(self, string, contexts=[], add_to_context=True, default_value="", left_wrapper="", right_wrapper=""):
        bstring = bytearray(string, 'utf-8')
        bleft_wrapper = bytearray(left_wrapper, 'utf-8')
        bright_wrapper = bytearray(right_wrapper, 'utf-8')
        delta = 0
        if not contexts:
            contexts = self.variables
        missing_vars = []
        for m in re.finditer('{{(.*?)}}', string):
            replacement = None
            for context in contexts:
                replacement = context.get(m.group(1))
                if replacement: break
            if not replacement:
                missing_vars.append(m.group(0))
                replacement = default_value
                if add_to_context:
                    context[m.group(0)] = replacement
            full_replacement = bleft_wrapper + bytearray(replacement, 'utf-8') + bright_wrapper
            bstring[m.start()+delta:m.end()+delta] = full_replacement
            delta += len(full_replacement) - len(m.group(0))
        return str(bstring, encoding='utf-8'), missing_vars

    def touch_variables(self, var_names):
        for var_name in var_names:
            if var_name not in self.variables:
                self.variables[var_name] = ''

    def set_variable(self, name, value):
        self.variables[name] = value

    def get_variable(self, name):
        if name not in self.variables:
            self.touch_variables([name])
        return self.variables[name]

    def get_variables(self, r):
        def req_var_generator(r):
            for step in r['steps']:
                resource = self.get_resource(step['resource'])
                for var_name in resource['input variables']:
                    yield var_name, self.get_variable(var_name)
                if step['override_data']:
                    override_data_name = f"{r['name']} {step['name']} data"
                    yield override_data_name, self.get_variable(override_data_name)
        def rsc_var_generator(r):
            for var_name in r['input variables']:
                yield var_name, self.variables.get(var_name, '')
        if r.get('steps') is not None:
            return dict(req_var_generator(r))
        else:
            return dict(rsc_var_generator(r))

    def delete_variable(self, var_name):
        del self.variables[var_name]

    def get_response_type(self, resource):
        return resource['output headers'].get('Content-Type', 'text/unknown')

    def get_response_object(self, resource):
        response_text = resource['output']
        response_type = resource['output headers'].get('Content-Type', 'text/plain')
        coerced_response = {}
        try:
            if 'json' in response_type:
                coerced_response = json.loads(response_text)
            elif 'xml' in response_type:
                coerced_response = xmltodict.parse(response_text)
            elif 'text' in response_type:
                coerced_response = json.loads('{ "root": '+ response_text + '}')
        except:
            exc = traceback.format_exc()
            print(exc)
            return {}
        return coerced_response

    def get_output_variable(self, resource, out_id):
        if type(out_id) is int and out_id < len(resource['output variables'].keys()):
            var_name = list(resource['output variables'].keys())[out_id]
        elif type(out_id) is str:
            var_name = out_id
        else:
            return None, None

        if var_name in resource['output variables']:
            if resource['output']:
                output_var_path = resource['output variables'][var_name]
                value = self.get_response_object(resource)
                for part in output_var_path:
                    value = value.get(part, None)
                    if value is None: break
                return var_name, value
        return None

    def add_resource(self, name='', url='', method='get', import_type=None, headers={'Content-Type':'text/plain'}, data=''):
        name = name or f'Resource {len(self.resource_ids)+1}'
        inputs = self.vars_in_string(url)
        r_id = str(uuid.uuid1())
        while r_id in self.resource_ids:
            r_id = str(uuid.uuid1())
        if r_id not in self.resource_ids:
            self.resource_ids.append(r_id)
            self.resources[r_id] = {
                'id': r_id,
                'name': name,
                'url': url,
                'input variables': inputs,
                'method': method,
                'import content': '',
                'import name': '',
                'import type': import_type,
                'header ids': [],
                'headers': {},
                'output': "",
                'output headers': {},
                'output variables': {},
                'data': data,
                'references': {}
            }
        for h_name, h_value in headers.items():
            self.add_header(self.resources[r_id], h_name, h_value)

        return self.resources[r_id]

    def get_resource(self, ri):
        if type(ri) is int:
            if len(self.resource_ids) and ri < len(self.resource_ids):
                return self.resources[self.resource_ids[ri]]
        elif type(ri) is str:
            return self.resources.get(ri, {})
        return {}

    def rename_resource(self, resource, new_name):
        self.resources[resource['id']]['name'] = new_name
        return True

    def change_resource(self, resource, new_url=None, new_headers={}, new_import_content=None, new_import_name=None, new_data=None):
        resource['url'] = new_url if new_url is not None else resource['url']
        resource['import content'] = new_import_content if new_import_content is not None else resource['import content']
        resource['import name'] = new_import_name if new_import_name is not None else resource['import name']
        resource['data'] = new_data if new_data is not None else resource['data']
        resource['headers'].update(new_headers)
        resource_fields = [resource['url'], resource['import content'], resource['import name'], resource['data']]
        resource_fields += [value[1] for value in resource['headers'].values()]
        field_vars = self.vars_in_list(resource_fields)
        output_vars = set(resource['output variables'].keys())
        resource['input variables'] = list(field_vars-output_vars)
        return True

    def delete_resource(self, resource):
        has_references = len(list(filter(lambda x: x > 0, [value for value in resource['references'].values()]))) > 0
        if not has_references:
            self.resource_ids.remove(resource['id'])
            del self.resources[resource['id']]
            return True
        else:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Resource in use")
            return False

    def add_header(self, resource, new_name, new_value):
        header_id = str(uuid.uuid1())
        if new_name in resource['headers']:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"Header {new_name} already exists in settings")
            return False
        resource['header ids'].append(header_id)
        resource['headers'][header_id] = [new_name, new_value]
        return header_id

    def set_header(self, resource, header_id, new_name, new_value):
        if not header_id in resource['header ids']:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Header does not exist in settings")
            return False
        resource['headers'][header_id] = [new_name, new_value]
        return True

    def delete_header(self, resource, header_id):
        print(f"Settings::delete_headers: resource header ids: {resource['header ids']}")
        if not header_id in resource['header ids']:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Header does not exist in settings")
            return False
        i = resource['header ids'].index(header_id)
        del resource['header ids'][i]
        del resource['headers'][header_id]
        return True

    def set_output(self, resource, output, output_headers={}, override=True):
        if not resource['output'] or override:
            resource['output'] = output
            resource['output headers'] = output_headers

    def set_output_var(self, resource, var_name, var_path, var_value=''):
        if var_value or var_name not in self.variables:
            self.set_variable(var_name, var_value)
        resource['output variables'][var_name] = var_path

    def add_request(self, name):
        request_id = str(uuid.uuid1())
        self.request_ids.append(request_id)
        self.requests[request_id] = {
            'id': request_id,
            'name': name,
            'steps': [],
            'step names': {}
        }
        return self.requests[request_id]

    def get_request(self, index):
        if index < len(self.request_ids)-1:
            return self.requests[self.request_ids[index]]
        else:
            return None

    def rename_request(self, request, new_name):
        self.requests[request['id']]['name'] = new_name
        return True

    def delete_request(self, request_id):
        for i, step in enumerate(self.requests[request_id]['steps']):
            self.delete_step(request_id, i)
        self.request_ids.remove(request_id)
        del self.requests[request_id]
        return True

    def add_step(self, request_id, step_name, resource_id, metadata_source='', override_data=False):
        if resource_id in self.resources:
            request = self.requests[request_id]
            if step_name not in request['step names']:
                request['step names'][step_name] = True
                step = {'name': step_name, 'resource': resource_id, 'override_data': override_data, 'metadata_source': metadata_source}
                request['steps'].append(step)
                refs = self.resources[resource_id]['references']
                refs[request_id] = refs.get(request_id, 0) + 1
                return step
        self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Please choose a unique name")
        return False

    def rename_step(self, request_id, step, new_step_name):
        request = self.requests[request_id]
        step_name = step['name']
        if step_name in request['step names']:
            del request['step names'][step_name]
            request['step names'][new_step_name] = True
            for a_step in request['steps']:
                if a_step['name'] == step_name:
                    a_step['name'] = new_step_name
                    return True
        else:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Step does not exist")
            return False

    def move_step(self, request_id, step_index, new_index):
        self.requests[request_id]['steps'].insert(new_index, self.requests[request_id]['steps'].pop(step_index))

    def delete_step(self, request_id, step_index):
        request = self.requests[request_id]
        name = request['steps'][step_index]['name']
        refs = self.resources[request['steps'][step_index]['resource']]['references']
        if refs.get(request_id, None) == 0:
            del refs[request_id]
        else:
            refs[request_id] = refs.get(request_id, 1) - 1
        del request['step names'][name]
        del request['steps'][step_index]
        return True