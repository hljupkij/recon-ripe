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

    meta = {
        'name': 'RIPE Netblocks Resolver',
        'author': 'WP (@fandorin)',
        'version': 'v0.0.4',
        'description': 'Resolves IP addresses to netblocks and updates the database with the results.',
        'comments': (
            'Note: Nameserver must be in IP form.',
            '\te.g. 1.2.3.4',
        ),
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
        'options': (
            ('nameserver', '8.8.8.8', 'yes', 'ip address of a valid nameserver'),
        ),
    }

    def module_run(self, ips):
        self.thread(ips)

    def module_thread(self, ip):
        description = ""
        json_resp = self.ripe_search_request(ip,"inetnum")

        inetnum = self.json_search(json_resp,"inetnum");
        netname = self.json_search(json_resp,"netname");
        descr = self.json_search(json_resp,"descr");
        country = self.json_search(json_resp,"country");
        admin = self.json_search(json_resp,"admin-c");

#        for attribute in data["objects"]["object"][0]["attributes"]["attribute"]:
#            name = attribute["name"]
#            if name == "inetnum":
#                    inetnum = attribute["value"]
            #        description += inetnum + ", "
#            elif name == "netname":
#                    netname = attribute["value"]
        description += netname + ", "
#        elif name == "descr":
#                    description += attribute["value"]
#        description += descr + ", ";
#            elif name == "country":
#                    country = attribute["value"]
#        description += country + ", "
#            elif name == "admin-c":
#                    admin = attribute["value"]
        description += admin + ", "

        self.output("I did found net with netname "+netname+" with IP range "+inetnum+" maintained by "+admin+" and located in "+country+" and following description: "+description)
        net = self.parse_inetnum_to_cidr(str(inetnum))
        self.output("Add following net: " + net)
        self.insert_netblocks(netblock=net,notes=description)

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

# Load JSON string and search it for attribute
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
