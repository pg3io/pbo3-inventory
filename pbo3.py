from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
    name: pbo3
    plugin_type: inventory
    short_description: Returns Ansible inventory from yaml
    description: Returns Ansible inventory from yaml
    options:
      plugin:
          description: gen inventory
          required: true
          choices: ['pbo3']
      api_url:
        description: api url
        type: string
        required: true
      username:
        description: username
        type: string
        required: true
      password:
        description: password
        type: string
      path_to_inventory:
        description: directory
        type: string
'''

login = """
mutation($identifier: String!, $password: String!) {
  login(input: { identifier: $identifier, password: $password }) {
    jwt
  }
}
"""

data_services = """
query($start: Int!) {
  services(start: $start) {
    id,
    name
  }
}
"""

data_vars = """
query($start: Int!) {
  globalVars(start: $start) {
      id,
      key,
      value
  }
}
"""

data_clients = """
query($start: Int!) {
  clients(start: $start) {
      id,
      name,
      infos
  }
}
"""

data = """query ($start: Int!, $where: JSON!){
  servers(start: $start, where: $where){
    id,
    hostname,
    date,
    archiveDate,
    archived,
    ansible_vars
    offer {
      id,
      name,
      hoster {
        id,
        name,
        url_admin
      }
    },
    ip,
    raid,
    infos,
    client {
      id,
      name,
      infos
    },
    os {
      id,
      os_name,
      os_version,
      version_name
    },
    cred {
      id,
      name,
      auth,
      token_hash,
      url_admin_custom,
      login,
      password_hash,
      hoster {
        id,
        name,
        url_admin
      }
    },
    type {
      id,
      name
    },
    env {
      id,
      name
    },
    dc {
      id,
      name,
      hoster {
        id,
        name,
        url_admin
      }
    }
    profile {
      id,
      name,
      infos
    },
    server_user {
      id,
      name
    },
    services {
      id,
      name
    }
  }
}"""

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_native
from ansible.module_utils._text import to_text
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable
import json
import requests
import getpass
import yaml
from copy import deepcopy


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):

    NAME = 'pbo3'
    
    def getToken(self, url, username, password):
        variables = {'identifier': username, 'password': password}
        try:
            response = requests.post(url, json={'query': login, 'variables': variables})
        except:
            print("Bad api url")
            return None
        if response.status_code != 200:
            print(str(response.status_code) + " - Bad repsonse")
            return None
        else:
            if 'errors' in response.text:
                print('Wrong username or password!')
                return None
            json_data = json.loads(response.text)
            token = json_data['data']['login']['jwt']
            return token

    def createHeaders(self, token):
        headers= {'Authorization': "Bearer " + token}
        return headers

    def getStrapi(self, url, query, headers, hasJson, table):
        start = 0
        result = {}
        queryList = []
        while start != -1:
            try:
                if hasJson is True:
                    r = requests.post(url, json={'query': query, 'variables': {'start': start, 'where': {'archived': False}} }, headers=headers )
                else: 
                    r = requests.post(url, json={'query': query, 'variables': {'start': start} }, headers=headers )
            except:
                return None
            if r.status_code != 200 or 'errors' in r.text:
                start = None
            elif r and r.text:
                start += 100
                if not(len(json.loads(r.text)["data"][table])):
                    start = -1
                queryList += (json.loads(r.text)["data"][table])
        result[table] = queryList
        return result

    def query(self, headers, query, url, hasJson, table):
        result = self.getStrapi(url, query, headers, hasJson, table)
        if result is None:
            print('Bad request!')
            return None
        else:
            return result

    def getClients(self, servers, clients):
        result = []
        for i in range(len(clients['clients'])):
            name = clients['clients'][i]['name']
            tmp = []    
            hostList = {}
            for k in range(len(servers['servers'])):
                if servers['servers'][k]['client'] is None:
                    continue
                if servers['servers'][k]['client']['name'] == clients['clients'][i]['name']:
                    tmp.append({servers['servers'][k]['hostname']: None})
            hostList[name] = {'hosts': tmp}
            result.append(hostList)
        return result

    def getServices(self, servers, services, result):
        for i in range(len(services['services'])):
            name = services['services'][i]['name']
            tmp = []
            hostList = {}
            for k in range(len(servers['servers'])):
                for n in range(len(servers['servers'][k]['services'])):
                    if servers['servers'][k]['services'][n]['name'] == services['services'][i]['name']:
                        tmp.append({servers['servers'][k]['hostname']: None})
            hostList[name] = {'hosts': tmp}
            result.append(deepcopy(hostList))
        return result

    def getServers(self, headers, data, url):
        servers = self.query(headers, data, url, True, 'servers')
        if servers is None:
            return
        return servers

    def getUsers(self, servers):
        result = []
        variables = {}
        for i in range(len(servers['servers'])):
            yaml_data = None
            variables = {}
            if (servers['servers'][i]['ansible_vars']):
                ansible = servers['servers'][i]['ansible_vars']
                if ansible is not None and len(ansible) > 0:
                    idx = -1
                    ansible_vars = ansible.split('\n')
                    for j in range(len(ansible_vars)):
                        tmp = ansible_vars[j].split(':')
                        if tmp[0] == 'ansible_user':
                            idx = j
                    if idx != -1:
                        ansible_vars.pop(idx)
                    ansible = "\n".join(ansible_vars)
                    yaml_data = yaml.safe_load(ansible)
                    for key, value in yaml_data.items():
                        variables[key] = value
            if servers['servers'][i]['server_user'] is not None and len(servers['servers'][i]['server_user']['name']) > 0:
                variables['ansible_user'] = servers['servers'][i]['server_user']['name']
            else:
                variables['ansible_user'] = 'admin'
            result.append({servers['servers'][i]['hostname'] : variables})
        return result

    def generate_inventory(self, url, username, password, path):
        token = self.getToken(url, username, password)
        if token is None:
            return
        headers = self.createHeaders(token)
        servers = self.getServers(headers, data, url)
        if servers is None:
            return
        clients = self.query(headers, data_clients, url, False, 'clients')
        if clients is None:
            return
        services = self.query(headers, data_services, url, False, 'services')
        if services is None:
            return
        inventory = {'all': {}}
        hostvars = self.getUsers(servers)
        inventory['all']['vars'] = hostvars
        result = self.getClients(servers, clients)
        result = self.getServices(servers, services, result)
        inventory['all']['children'] = result
        json_data = json.dumps(inventory, indent=2)
        return json_data

    def parseValues(self, s):
        array = s.split('\n')
        arr = []
        if len(array) == 1:
            return s
        else:
            for i in range(len(array)):
                a = array[i].split(' ')
                arr.append(a[3])
            return arr

    def getVars(self, headers, url):
        data = self.query(headers, data_vars, url, False, 'globalVars')
        result = {}
        count = 0
        if data is None:
            return {'ansible_user': 'admin'}
        if len(data['globalVars']) == 0:
            return {'ansible_user': 'admin'}
        for i in range(len(data['globalVars'])):
            if data['globalVars'][i]['key'] != 'ansible_user':
                values = deepcopy(self.parseValues(data['globalVars'][i]['value']))
                result[data['globalVars'][i]['key']] = deepcopy(values)
            else:
                values = deepcopy(self.parseValues(data['globalVars'][i]['value']))
                result[data['globalVars'][i]['key']] = deepcopy(values)
                count += 1
        if count == 0:
            result[data['globalVars'][i]['key']] = {'ansible_user': 'admin'}
        return result

    def _populate(self):
        try:
            path = self.get_option('path_to_inventory')
            username = self.get_option('username')
            url = self.get_option('api_url')
            if path is None:
                path = "./hosts.json"
            password = self.get_option('password')
            if password is None:
                password = getpass.getpass()
            headers = self.createHeaders(self.getToken(url, username, password))
            gVars = self.getVars(headers, url)
            json_data = json.loads(self.generate_inventory(url, username, password, path))
            for i in range(len(json_data['all']['children'])):
                for key, value in json_data['all']['children'][i].items() :
                    name = key
                self.inventory.add_group(name)
                for x in range(len(json_data['all']['children'][i][name]['hosts'])):
                    for key, value in json_data['all']['children'][i][name]['hosts'][x].items():
                        self.inventory.add_host(host=key, group=name)
                        for k in range(len(json_data['all']['vars'])):
                            for var_key, var_value in json_data['all']['vars'][k].items():
                                if(var_key == key):
                                    for k, v in var_value.items():
                                        self.inventory.set_variable(key, k, v)
            for k, v in gVars.items():
                self.inventory.set_variable('all', k, v)  

        except Exception as e:
            raise AnsibleError('Unable to fetch hosts from PBO3, this was the original exception: %s' % to_native(e), orig_exc=e)

    def verify_file(self, path):
        return (
            super(InventoryModule, self).verify_file(path) and
            path.endswith(('inventory.yaml', 'inventory.yml')))

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)
        self._populate()
