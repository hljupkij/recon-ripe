# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.resolver import ResolverMixin
from recon.mixins.threads import ThreadingMixin
# module specific imports
import os
import json
import time

class Module(BaseModule, ResolverMixin, ThreadingMixin):

    meta = {
        'name': 'Robtex  Resolver',
        'author': 'WP (@fandorin)',
        'version': '0.1',
        'description': 'Resolves IP addresses to hosts from Robtex database and updates the database with the results.',
        'dependencies': [],
        'files': [],
#        'required_keys': ['robtex_api', 'robtex_secret'],
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL'
    }

    def module_run(self, ips):
        self.thread(ips)

    def module_thread(self, ip):
        time.sleep(1)
        description = ""
        resp = self.request(url='https://freeapi.robtex.com/ipquery/'+ip,headers={'Accept': 'application/json'}, method='GET')

#        self.debug("Got a response: " + resp.text)
        hostnames_list = self.json_search(resp.text,"o")
        self.debug("List of hostnames: " + str(hostnames_list))
        for hostname in hostnames_list:
            self.verbose('Insert '+hostname + " for IP "+ip)
            self.insert_hosts(host=hostname,ip_address=ip)

# Load JSON string and search it for attribute
    def json_search(self, json_string, searchAttr):
        result = []
        if (json_string == ""):
            return result
        try:
            data = json.loads(json_string)
            self.debug("Number of objects: " + str(len(data["pas"])))
            for element in data["pas"]:
                self.debug("Object:" +str(element))
                result.append(element[searchAttr])
        except:
            self.error("Could not find a valid JSON in response!")
        return result
