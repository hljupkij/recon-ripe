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
        'name': 'RIPE Netblocks Resolver',
        'author': 'WP (@me)',
        'version': 'v0.0.2',
        'description': 'Resolves IP addresses to nethosts and updates the database with the results.',
        'comments': (
            'Note: Nameserver must be in IP form.',
            '\te.g. 1.2.3.4',
        ),
        'query': 'SELECT DISTINCT ip_address FROM hosts WHERE ip_address IS NOT NULL',
        'options': (
            ('nameserver', '8.8.8.8', 'yes', 'ip address of a valid nameserver'),
        ),
    }
    #search_result = ""
    # "query" is optional and determines the "default" source of input
    # the "SOURCE" option is only available if "query" is defined

    # "options" expects a tuple of tuples containing 4 elements:
    # 1. the name of the option
    # 2. the default value of the option (strings, integers and boolean values are allowed)
    # 3. a boolean value (True or False) for whether or not the option is mandatory
    # 4. a description of the option

    # optional method
    def module_pre(self):
        # override this method to execute code prior to calling the "module_run" method
        # returned values are passed to the "module_run" method and must be captured in a parameter

	# extend the "netblocks"-table
        try:
            self.query("ALTER TABLE netblocks ADD COLUMN admin TEXT")
        except Exception as e:
            print("[*] Column in table most likely exists. Error returned: " + str(e))

        try:
            self.query("ALTER TABLE netblocks ADD COLUMN netname TEXT")
        except Exception as e:
            print("[*] Column in table most likely exists. Error returned: " + str(e))

        try:
            self.query("ALTER TABLE netblocks ADD COLUMN country TEXT")
        except Exception as e:
            print("[*] Column most likely exists.  Error returned: " + str(e))

        try:
            self.query("ALTER TABLE netblocks ADD COLUMN description TEXT")
        except Exception as e:
            print("[*] Column most likely exists.  Error returned: " + str(e))

        return 1

    # mandatory method
    # the second parameter is required to capture the result of the "SOURCE" option, which means that it is only required if "query" is defined within "meta"
    # the third parameter is required if a value is returned from the "module_pre" method
    def module_run(self, ips, value):
        # do something leveraging the api methods discussed below
        # local option values can be accessed via self.options['name']
        # use the "self.workspace" class property to access the workspace location
        # threading can be used anywhere with the module through the usage of the "self.thread" api call
        # the "self.thread" api call requires a "module_thread" method which acts as the worker for each item in a queue
        # "self.thread" takes at least one argument
        # the first argument must be an iterable that contains all of the items to fill the queue
        # all other arguments get blindly passed to the "module_thread" method where they can be accessed at the thread level
        self.thread(ips)

    # optional method
    # the first received parameter is required to capture an item from the queue
    # all other parameters passed in to "self.thread" must be accounted for
    def module_thread(self, ip):
        # never catch KeyboardInterrupt exceptions in the "module_thread" method as threads don't see them
        # do something leveraging the api methods discussed below
#        self.output('Search netblock for '+ip)
        resp = self.request('https://rest.db.ripe.net/search.json?query-string='+ip+'&type-filter=inet6num&type-filter=inetnum&flags=no-irt&flags=no-filtering&flags=no-referenced', method='GET', headers={'Accept': 'application/json'})

    	if resp.status_code != 200:
    	    self.output('Got error response:'+str(resp.status_code))
            exit;

	#print resp.json
	#self.output("JSON data:"+str(resp.json()["objects"]))
#    for name, series in resp.json()["objects"].iteritems():
#        print series["type"]

        data = json.loads(resp.text,"UTF-8")
        #self.parse_object(data)
#        self.search_key(data,"objects")
        resp_type = data["objects"]["object"][0]["type"]
#        self.output("\nResponse type: "+resp_type)
        if resp_type != "inetnum":
            self.output("something got wrong, there is no inetnum in response...")
            exit;

        description = ""

        for attribute in data["objects"]["object"][0]["attributes"]["attribute"]:
            name = attribute["name"]
            if name == "inetnum":
                    inetnum = attribute["value"]
            elif name == "netname":
                    netname = attribute["value"]
            elif name == "descr":
                    description += attribute["value"]
		    description += ", "
            elif name == "country":
                    country = attribute["value"]
            elif name == "admin-c":
                    admin = attribute["value"]

        self.output("I did found net with netname "+netname+" with IP range "+inetnum+" maintained by "+admin+" and located in "+country+" and following description: "+description)
        net = self.parse_inetnum_to_cidr(str(inetnum))
        self.output("Add following net: " + net)
        self.add_netblocks(netblock=net)
	self.query('UPDATE netblocks SET admin=?, netname=?, country=?, description=? WHERE netblock=?',(admin, netname,country,description, net))
#        print str(data["objects"]['object'][0]['link']['href'])

# Parse string
    def parse_inetnum_to_cidr(self,inetnum):
#        print "\nPassed string: "+inetnum
        matches = re.findall('((\d{1,3}\.?){4})',inetnum)

#        print "\nFound "+str(len(matches))+" IPs"
#        for match in matches:
#            self.output("Matched IP: "+str(match[0]))

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
