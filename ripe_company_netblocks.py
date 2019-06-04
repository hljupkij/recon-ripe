# Module for recon-ng to resolve ip addresses to netblocks, administrated by RIPE.
# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
from recon.mixins.resolver import ResolverMixin
from recon.mixins.threads import ThreadingMixin
# module specific imports
from urlparse import urlparse
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
        'name': 'RIPE Netblock Search',
        'author': 'WP (@bitinspect)',
        'version': 'v0.0.1',
        'description': 'Resolves netblocks of company.',
        'query': 'SELECT DISTINCT company FROM companies WHERE company IS NOT NULL',
    }
    #search_result = ""
    # "query" is optional and determines the "default" source of input
    # the "SOURCE" option is only available if "query" is defined

    # "options" expects a tuple of tuples containing 4 elements:
    # 1. the name of the option
    # 2. the default value of the option (strings, integers and boolean values are allowed)
    # 3. a boolean value (True or False) for whether or not the option is mandatory
    # 4. a description of the option

# Add additional columns to contacts table
    def add_columns(self, ):
        try:
            self.query("ALTER TABLE netblocks ADD COLUMN email,phone,fax,handle TEXT")
        except Exception as e:
            print("[*] Column most likely exists.  Error returned: " + str(e))

# Send JSON request to RIPE
    def ripe_full_search(self, Query, searchType, searchAttr):
        payload = {'home_search':'home_search','home_search:doSearch':'Search','home_search:searchform_q':Query}
        resp = self.request('https://apps.db.ripe.net/search/full-text.html',method='POST',payload=payload)

# Send JSON request to RIPE
    def ripe_json_request(self, Query, searchType, searchAttr):

        resp = self.request('https://rest.db.ripe.net/search.json?query-string='+Query+'&type-filter='+searchType+'&flags=no-irt&flags=no-filtering&flags=no-referenced', method='GET', headers={'Accept': 'application/json'})

    	if resp.status_code != 200:
    	    self.output('Got error response:'+str(resp.status_code))
            exit

        data = json.loads(resp.text,"UTF-8")
        resp_type = data["objects"]["object"][0]["type"]
        if resp_type != searchType:
            print("something got wrong, there is no "+str(searchType)+" in response, instead this object is of type "+str(resp_type))
            exit

        result = ""
        for attribute in data["objects"]["object"][0]["attributes"]["attribute"]:
            name = attribute["name"]
            if name == searchAttr:
                    result += attribute["value"]

        print("I searched for attribute "+str(searchAttr)+" and of type "+str(searchType)+" and found "+str(result))
        return result

    # optional method
    def module_pre(self):
        # override this method to execute code prior to calling the "module_run" method
        # returned values are passed to the "module_run" method and must be captured in a parameter
        return 1

    # mandatory method
    # the second parameter is required to capture the result of the "SOURCE" option, which means that it is only required if "query" is defined within "meta"
    # the third parameter is required if a value is returned from the "module_pre" method
    def module_run(self, companies, value):
        self.thread(companies)

    # optional method
    # the first received parameter is required to capture an item from the queue
    # all other parameters passed in to "self.thread" must be accounted for
    def module_thread(self, company):
        ipv4_net = self.ripe_json_request(company, "inetnum", "inetnum")
	net = self.parse_inetnum_to_cidr(str(ipv4_net))
        self.output("I did found "+ipv4_net)
	self.add_netblocks(net)

# Parse string
    def parse_inetnum_to_cidr(self,inetnum):
#        print "\nPassed string: "+inetnum
        matches = re.findall('((\d{1,3}\.?){4})',inetnum)

        if len(matches) == 2:
            start = matches[0][0]
            end = matches[1][0]
            if(len(start.split(".")) == len(end.split("."))):
                int_start = map(int, start.split("."))
                int_end = map(int, end.split("."))
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
