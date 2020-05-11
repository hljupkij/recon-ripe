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
        'description': 'Search netblocks by maintainer and updates the database with the results.',
        'query': 'SELECT DISTINCT notes FROM contacts WHERE notes LIKE "%-RIPE"',
    }

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

    def module_run(self, items):
        self.thread(items)

    def module_thread(self, handle):
        result_list_json = self.ripe_search_request(handle, "inetnum")

        for item in result_list_json:
            net_handle = self.json_search(item,"lookup-key")
            netblock = self.parse_inetnum_to_cidr(net_handle)
            self.output("I did found " + net_handle)

            if (net_handle != "" and self.json_search(item,"object-type") == "inetnum"):
                admin_handle = self.json_search(item,"admin-c")
                tech_handle = self.json_search(item,"tech-c")
                netname = self.json_search(item,"netname")
                country = self.json_search(item,"country")
                description = self.json_search(item,"descr")

                last_modified = self.json_search(item,"last-modified")

                notes = "%s, %s, %s, %s, %s" % (netname, description, country, admin_handle, tech_handle)
#                self.output("First: %s Middle: %s Last: %s" % (first_name, middle_name, last_name))
                self.insert_netblocks(netblock=netblock,notes=notes)

# Parse string
    def parse_inetnum_to_cidr(self,inetnum):
#        print "\nPassed string: "+inetnum
        matches = re.findall('((\d{1,3}\.?){4})',inetnum)

        if len(matches) == 2:
            start = matches[0][0]
            end = matches[1][0]
            if(len(start.split(".")) == len(end.split("."))):
                int_start = list(map(int, start.split(".")))
                int_end = list(map(int, end.split(".")))
#                print("Start IP:"+str(len(int_start)))
                number_start = 0
                number_end = 0

                for i in range(0,4):
                    number_start += int_start[i]*256**(3-i)
                    number_end += int_end[i]*256**(3-i)

                number =number_end - number_start +1
                cidr = int(32 - math.log(number,2))
#                print("Inetnum: "+str(inetnum)+" Number: "+ str(number)+" CIDR: "+str(cidr))
                net = str(start)+"/"+str(cidr)
                return net
