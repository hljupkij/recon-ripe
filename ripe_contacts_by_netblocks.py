# Module for recon-ng to resolve ip addresses to netblocks, administrated by RIPE.
# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.resolver import ResolverMixin
from recon.mixins.threads import ThreadingMixin
# module specific imports
from urllib import parse
import os
import json
import re
import ipaddress
import math

class Module(BaseModule, ResolverMixin, ThreadingMixin):

    # modules are defined and configured by the "meta" class variable
    # "meta" is a dictionary that contains information about the module, ranging from basic information, to input that affects how the module functions
    # below is an example "meta" declaration that contains all of the possible definitions
    # all items are optional and may be omitted

    meta = {
        'name': 'RIPE Contacts search',
        'author': 'WP (@fandorin)',
        'version': 'v0.0.4',
        'description': 'Resolves maintainer of netblocks and updates the database with the results.',
        'query': 'SELECT DISTINCT netblock FROM netblocks WHERE netblock IS NOT NULL',
    }

# Send search request to RIPE
    def ripe_search_request(self, Query, searchType):
        result = ""
        resp = self.request(url='https://rest.db.ripe.net/search.json?query-string='+Query+'&type-filter='+searchType+'&flags=no-irt&flags=no-filtering&flags=no-referenced', headers={'Accept': 'application/json'}, method='GET')

        if resp.status_code == 200:
            try:
                data = json.loads(resp.text)
                resp_type = data["objects"]["object"][0]["type"]
                if resp_type != searchType:
                    self.error("something got wrong, there is no "+str(searchType)+" in response, instead this object is of type "+str(resp_type))
                else:
                    result = resp.text
            except:
                self.error("Could not find a valid JSON in response!")
        else:
            self.alert('Got error response: %s for search %s of type %s' % (str(resp.status_code), Query, searchType) )

        return result

    def json_search(self, json_string, searchAttr):
        result = ""
        if (json_string == ""):
            return result
        try:
            data = json.loads(json_string)
            for attribute in data["objects"]["object"][0]["attributes"]["attribute"]:
                if attribute["name"] == searchAttr:
                    result += attribute["value"]
        except:
            self.error("Could not find a valid JSON in response!")
        return result

    def module_run(self, nets):
        self.thread(nets)

    def module_thread(self, net):
        json_admin_handle = self.ripe_search_request(net, "inetnum")
        admin_handle = self.json_search(json_admin_handle,"admin-c")

        self.output("I did found " + admin_handle)
        if (admin_handle != ""):

            admin_person = self.ripe_search_request(admin_handle,"person")
            if (admin_person != ""):
                admin_name = self.json_search(admin_person,"person")
                admin_address = self.json_search(admin_person,"address")
                admin_phone = self.json_search(admin_person,"phone")
                admin_fax = self.json_search(admin_person,"fax-no")
                admin_mail = self.json_search(admin_person,"e-mail")

                self.output("I did found %s with address %s, phone %s, fax %s and mail %s" % (admin_name, admin_address, admin_phone, admin_fax, admin_mail))
                first_name = admin_name.split(" ",1)[0]
                last_name = admin_name.rsplit(" ",1)[1]
                middle_name = admin_name.strip(first_name).rstrip(last_name)

                self.output("First: %s Middle: %s Last: %s" % (first_name, middle_name, last_name))
                self.insert_contacts(first_name=first_name, middle_name = middle_name, last_name=last_name,email=admin_mail,notes=admin_handle)
