import re
import json
import xmltodict
import os
import uuid
import traceback
from functools import partial, reduce

import nanome
from nanome.util import Logs
BASE_PATH = os.path.dirname(os.path.realpath(__file__))
MENU_PATH = os.path.join(BASE_PATH, 'menus', 'json', 'Settings.json')
OFF_ICON_PATH = os.path.join(BASE_PATH, 'assets', 'icons', 'off.png')
ON_ICON_PATH = os.path.join(BASE_PATH, 'assets', 'icons', 'on.png')

class Settings():

    def __init__(self, plugin):
        self.plugin = plugin
        self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        # uid -> [name, value]
        self.variables = {}
        # name -> uid
        self.variable_names = {}
        # value -> [uid]
        self.variable_values = {}
        self.resource_ids = []
        self.resources = {}
        self.request_ids = []
        self.requests = {}
        self.__settings = {}

        self.count = 0

        self.__settings_path = os.path.normpath(os.path.join(plugin.plugin_files_path, 'postnome', 'settings.json'))
        if not os.path.exists(os.path.dirname(self.__settings_path)):
            os.makedirs(os.path.dirname(self.__settings_path))
        self.load_settings()

    def generate_settings(self):
        for setting_name in ['variables', 'variable_names', 'variable_values', 'resource_ids', 'resources', 'request_ids', 'requests']:
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
        Logs.debug(f'settings: {self.__settings_path}')

    def touch_value(self, var_value):
        if not self.variable_values.get(var_value, None):
            self.variable_values[var_value] = []

    
    def touch_variable(self, var_name, uid=None):
        if var_name not in self.variable_names:
            uid = uid or str(uuid.uuid1())
            self.variable_names[var_name] = uid
            self.touch_value('')
            self.variable_values[''].append(uid)
            self.variables[uid] = [var_name,'']
            return uid
        else:
            return self.variable_names[var_name]

    def set_variable(self, uid=None, name=None, value=None):
        # create the variable if it doesn't exist
        if uid is None and name is not None:
            uid = self.touch_variable(name)
        # default to existing values
        name = self.variables.get(uid, ['', ''])[0] if name is None else name
        value = self.variables.get(uid, ['', ''])[1] if value is None else value
        # update value->uid mappings
        old_value = self.variables[uid][1]
        self.variable_values[old_value].remove(uid)
        if not self.variable_values[old_value]:
            del self.variable_values[old_value]
        if not self.variable_values.get(value, None):
            self.variable_values[value] = []
        self.variable_values[value].append(uid)
        # update uid->name,value mapping
        self.variables[uid] = [name, value]
        return uid

    def get_variable_name(self, uid):
        if uid in self.variables:
            return self.variables[uid][0]
        return None

    def get_variable_by_id(self, uid):
        if uid in self.variables:
            var = self.variables[uid]
            return self.variables[uid][1]
        return None

    def get_variable_by_name(self, name):
        if name not in self.variable_names:
            self.touch_variable(name)
        uid = self.variable_names[name]
        return self.variables[uid][1]

    def get_inputs(self, r):
        def request_var_generator(r):
            for step in r['steps']:
                resource = self.get_resource(step['resource'])
                for var_id in resource['input variables']:
                    yield var_id, self.variables.get(var_id, [None, None])
                if step['override_data']:
                    override_data_name = f"{r['name']} {step['name']} data"
                    var_id = self.touch_variable(override_data_name)
                    yield var_id, self.variables.get(var_id, [None, None])
        def resource_var_generator(r):
            for var_id in r['input variables']:
                yield var_id, self.variables.get(var_id, [None, None])

        if r.get('steps') is not None:
            return dict(request_var_generator(r))
        else:
            return dict(resource_var_generator(r))

    def delete_variable_by_name(self, var_name):
        uid = self.variable_names[var_name]
        self.delete_variable_by_id(uid, var_name)

    def delete_variable_by_id(self, var_id, var_name=''):
        value = self.variables[var_id][1]
        var_name = var_name or self.variables[var_id][0]
        del self.variable_names[var_name]
        self.variable_values[value].remove(var_id)
        del self.variables[var_id]

    def generate_resource_string(self, string, acc=None):
        """ Takes a variable name template string and returns a variable uid
            template string, matching known variables to their corresponding uids
            and generating new ones for variables that do not exist\n
            Keyword arguments:\n
            string -- The variable string to convert. Of the form: 'I am a {{variable}} string'\n
            acc   --  An optional accumulator function that takes one argument: the uid of a variable found within string.
            This function will be called once per variable found in string.
        """
        def uuid_gen(var_name): 
            uid = self.touch_variable(var_name)
            if acc is not None: acc(uid, var_name)
            return uid
        return self.contextualize(string, [self.variable_names], defaults_generator=uuid_gen, reporter=acc, left_wrapper="{{", right_wrapper="}}")

    def generate_varname_string(self, string, acc=None):
        def uuid_gen(uid, var_name):
            self.touch_variable(var_name, uid=uid)
            if acc is not None: acc(uid)
            return uid
        return self.contextualize(string, defaults_generator=uuid_gen, reporter=acc, left_wrapper="{{", right_wrapper="}}", use_index=0)

    def contextualize(self, string, contexts=[], add_to_context=False, default_value="", defaults_generator=None, reporter=None, left_wrapper="", right_wrapper="", use_index=1):
        bstring = bytearray(string, 'utf-8')
        bleft_wrapper = bytearray(left_wrapper, 'utf-8')
        bright_wrapper = bytearray(right_wrapper, 'utf-8')
        delta = 0
        if not contexts:
            contexts = [self.variables]
        for m in re.finditer('{{(.*?)}}', string):
            replacement = None
            for context in contexts:
                replacement = context.get(m.group(1))
                if type(replacement) is list: 
                    replacement = replacement[use_index]
                if replacement: break
            if replacement: 
                if reporter: reporter(m.group(1), replacement)
            else:
                replacement = defaults_generator(m.group(1)) if defaults_generator else default_value
                if add_to_context:
                    context[m.group(1)] = replacement
            full_replacement = bleft_wrapper + bytearray(replacement, 'utf-8') + bright_wrapper
            bstring[m.start()+delta:m.end()+delta] = full_replacement
            delta += len(full_replacement) - len(m.group(0))
        return str(bstring, encoding='utf-8')

    def decontextualize(self, json, contexts=[], left_wrapper="{{", right_wrapper="}}", k_or_v=False):
        def replace(json, old, new, k_or_v=False):
            newd = {}
            print("JSON:")
            print(json)
            for k, v in json.items():
                if k_or_v:
                    if v == old:
                        newd[k] = new
                    else:
                        newd[k] = v
                if isinstance(v, dict):
                    v = replace(v, old, new, k_or_v)
                if not k_or_v:
                    if k == old:
                        newd[new] = v
                    else:
                        newd[k] = v
            return newd

        if not contexts:
            contexts = [self.variable_values]
        for context in contexts:
            for var_value, var_names in context.items():
                Logs.debug(f'replacing {var_value} with {var_names[0]}')
                json = replace(json, var_value, left_wrapper+var_names[0]+right_wrapper, k_or_v)
        return json

    def decontextualize_string(self, string, contexts=[], left_wrapper="{{", right_wrapper="}}", use_index=0):
        for context in contexts:
            for var_value, var_names in context.items():
                string = string.replace(var_value, left_wrapper+var_names[use_index]+right_wrapper)
        return string

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
            Logs.debug(exc)
            return {}
        return coerced_response

    def get_output_variable(self, resource, out_id):
        """ Gets an output variable from a resource by an id
            Keyword arguments:
            resource -- the resource to get the output variable from
            out_id   -- the index or the uuid of the output variable to get
        """
        if type(out_id) is int and out_id < len(resource['output variables'].keys()):
            var_id = list(resource['output variables'].keys())[out_id]
        elif type(out_id) is str:
            var_id = out_id
        else:
            return None, None

        if var_id in resource['output variables']:
            if resource['output']:
                # [ {{mol_name}}, {{proj_id}}, 1, MOLFILE]
                output_var_path = resource['output variables'][var_id]
                value = self.get_response_object(resource)
                for part in output_var_path:
                    value = value.get(part, None)
                    if value is None: break
                return var_id, value
        return None

    def add_resource(self, name='', url='', method='get', import_type=None, headers={'Content-Type':'text/plain'}, data=''):
        name = name or f'Resource {len(self.resource_ids)+1}'
        inputs = []
        def acc(name, uid): inputs.append(uid)
        self.generate_resource_string(url, acc=acc)
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
    
    def get_resource_item(self, resource, item_name):
        """ Returns an item from a resource with named variables instead of uids
        """
        cstr = partial(self.contextualize, left_wrapper="{{", right_wrapper="}}", use_index=0)
        if item_name in ['url', 'import name', 'import content', 'data']:
            value = cstr(resource.get(item_name, ''))
        elif item_name == 'headers':
            uid_headers = resource.get('headers', {})
            value = {h_id:[cstr(h_name), cstr(h_value)] for h_id, [h_name, h_value] in uid_headers.items()}
        return value

    def set_resource_item(self, resource, item_name, item):
        """ Transforms the given item from using named variables to uids and
            assigns this transformed item to the resource
        """
        uids = []
        def uid_acc(name, uid): 
            Logs.debug('item:', item)
            Logs.debug('uid:', uid)
            uids.append(uid)
        rstr = partial(self.generate_resource_string, acc=uid_acc)
        if type(item) is str:
            value = rstr(item)
            resource[item_name] = value
        elif type(item) is list:
            value = {h_id: [rstr(h_n), rstr(h_v)] for h_id, [h_n, h_v] in item.values()}
            resource[item_name].update(value)
        return uids

    def rename_resource(self, resource, new_name):
        self.resources[resource['id']]['name'] = new_name
        return True

    def change_resource(self, resource, new_url=None, new_headers={}, new_import_content=None, new_import_name=None, new_data=None):
        input_vars = set()
        def acc(uid, name): input_vars.add(uid)

        if new_url is not None:
            input_vars.update(self.set_resource_item(resource, 'url', new_url))
        else:
            self.generate_varname_string(resource['url'], acc)

        if new_import_name is not None:
            input_vars.update(self.set_resource_item(resource, 'import name', new_import_name))
        else:
            self.generate_varname_string(resource['import name'], acc)

        if new_import_content is not None:
            input_vars.update(self.set_resource_item(resource, 'import content', new_import_content))
        else:
            self.generate_varname_string(resource['import content'], acc)

        if new_data is not None:
            input_vars.update(self.set_resource_item(resource, 'data', new_data))
        else:
            self.generate_varname_string(resource['data'], acc)

        if new_headers is not None:
            input_vars.update(self.set_resource_item(resource, 'headers', new_headers))
        else:
            for name, value in resource['headers'].values():
                self.generate_varname_string(name, acc)
                self.generate_varname_string(value, acc)
            
        output_vars = set(resource['output variables'].keys())
        print(f"output_vars: {output_vars}")
        print(f"input_vars: {input_vars}")
        print(f"new url: {new_url}")
        resource['input variables'] = list(input_vars-output_vars)
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
        if not header_id in resource['header ids']:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Header does not exist in settings")
            return False
        i = resource['header ids'].index(header_id)
        del resource['header ids'][i]
        del resource['headers'][header_id]
        return True

    def set_output(self, resource, output, output_headers={}, override=True):
        """ Decontextualizes and sets the output for a resource
            and updates its output variables.
        """
        if not resource['output'] or override:
            resource['output headers'] = output_headers
            output = self.decontextualize_output(resource, json.loads(output))
            resource['output'] = json.dumps(output)
            for uid, path in resource['output variables'].items():
                value = output
                for part in path:
                    value = value.get(part, None)
                if value:
                    self.set_variable(uid, None, value)

    def decontextualize_output(self, resource, output):
        Logs.debug('input variables:')
        Logs.debug(resource['input variables'])
        for inp in resource['input variables']:
            Logs.debug("variable name:")
            Logs.debug(inp)
            Logs.debug('variable value:')
            Logs.debug(self.get_variable_by_id(inp))
        contexti = {self.variables[uid][1]:[uid] for uid in resource['input variables']}
        contexto = {self.variables[uid][1]:[uid] for uid in resource['output variables']}
        output = self.decontextualize(output, [contexti], k_or_v=False)
        output = self.decontextualize(output, [contexto], k_or_v=True)
        return output

    def decontextualize_output_path(self, resource, output, path):
        context = {self.variables[uid][1]:[uid] for uid in resource['output variables']}
        path = [self.decontextualize(part, [context]) for part in path]
        return path

    def set_output_variable(self, resource, var_uid, var_name, var_path, var_value=''):
        if var_value is not None or var_uid not in self.variables:
            var_uid = self.set_variable(var_uid, var_name, var_value)
        resource['output variables'][var_uid] = var_path

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