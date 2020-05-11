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
        'description': 'Search maintainer/admins by companies name and updates the database with the results.',
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
    }

    def module_run(self, company):
        self.thread(company)

    def module_thread(self, company):
        result_list_json = self.ripe_search_request(company, "person")

        for item in result_list_json:
            admin_handle = self.json_search(item,"lookup-key")
            self.output("I did found " + admin_handle)

            if (admin_handle != "" and self.json_search(item,"object-type") == "person"):
                admin_name = self.json_search(item,"person")
                admin_address = self.json_search(item,"address")
                admin_phone = self.json_search(item,"phone")
                admin_fax = self.json_search(item,"fax-no")
                admin_mail = self.json_search(item,"e-mail")

                self.output("I did found %s with address %s, phone %s, fax %s and mail %s" % (admin_name, admin_address, admin_phone, admin_fax, admin_mail))
                first_name = admin_name.split(" ",1)[0]
                last_name = admin_name.rsplit(" ",1)[1]
                middle_name = admin_name.strip(first_name).rstrip(last_name)

                self.output("First: %s Middle: %s Last: %s" % (first_name, middle_name, last_name))
                self.insert_contacts(first_name=first_name, middle_name = middle_name, last_name=last_name,email=admin_mail,notes=admin_handle)

# Send full-text search request to RIPE
    def ripe_search_request(self, Query, searchType):
        result = [];
        resp = self.request(url='https://apps.db.ripe.net/db-web-ui/api/rest/fulltextsearch/select?facet=true&format=json&hl=true&q=('+Query+')%20AND%20(object-type:'+searchType+")",headers={'Accept': 'application/json'}, method='GET')
#        resp = self.request(url='https://rest.db.ripe.net/search.json?query-string='+Query+'&type-filter='+searchType, headers={'Accept': 'application/json'}, method='GET')

        if resp.status_code == 200:
            self.debug("Response:" + resp.text);
            try:
                data = json.loads(resp.text)
                number_of_results = data["result"]["numFound"]
                self.verbose("Number of results: "+str(number_of_results))
                if number_of_results == 0:
                    self.verbose("Nothing found");
                    return result;
                for i in range(number_of_results):
                    self.debug("Result Nr:"+str(i)+" : "+str(data["result"]["docs"][i]))
#                    resp_type = data["result"]["docs"][i]["strs"]["str"]["object-type"]
#                    if resp_type != searchType:
#                        self.error("something got wrong, there is no "+str(searchType)+" in response, instead this object is of type "+str(resp_type))
#                    else:
                    result.append(data["result"]["docs"][i]);
            except ValueError as e:
                self.error("Could not find a valid JSON in response!" + e.msg+" on line Nr: "+ e.pos+" :line: "+e.lineno)
        else:
            self.alert('Got error response: %s for search %s of type %s' % (str(resp.status_code), Query, searchType) )
        return result

    def json_search(self, json_obj, searchAttr):
        self.debug("Input JSON string:"+str(json_obj));
        result = ""
        try:
#            data = json.loads(json_string)
            for attribute in json_obj["doc"]["strs"]:
                if attribute["str"]["name"] == searchAttr:
                    result += attribute["str"]["value"]
        except ValueError as e:
            self.error("Could not find a valid JSON in response!" + e.msg+" on line Nr: "+ e.pos+" :line: "+e.lineno)
        return result
