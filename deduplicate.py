from recon.core.module import BaseModule
import codecs
import os

class Module(BaseModule):

    meta = {
        'name': 'DB Deduplicator',
        'author': ' (@hljupkij)',
        'version': '0.1',
        'description': 'Removes duplicate records from the database.',
        'options': (
            ('table', 'hosts', True, 'source table of data for the list'),
            ('column', 'ip_address', True, 'source column to compare items'),
            ('nulls', True, False, 'remove rows from the dataset with empty column'),
            ('filename', False, False, 'path and filename for remove strings'),
        ),
    }

    def deduplicate(self,table,column,item):
        #self.output("Start to remove duplicated rows")
        query = f'SELECT rowid,{table[:-1]},{column} FROM "{table}" WHERE {table[:-1]}=="{item[0]}" AND {column}=="{item[1]}" ORDER BY rowid'
        #self.output(query)
        rows = self.query(query)
        count = 0

        if len(rows) > 1:
            print(f'Found {len(rows)} duplicates of {rows[0][1]}')
            first_rowid = rows[0][0]
            for row in rows:
                #row = row if row else ''
                #print(row)
                if row[0] != first_rowid:
                    query = f'DELETE FROM {table} WHERE rowid == "{row[0]}"'
                    self.query(query)
                    count +=1
                    #print(f'{table[:-1]}:{row[1]}, {column}:{row[2]}')
            self.output(f"{count} items removed from '{table}'.")
        #self.output("End of remove duplicated rows")

    def remove_special(self,table,column,filename):
        self.output("Start to remove rows which contains defined strings")
        with codecs.open(filename, 'r', encoding='utf-8') as infile:
            for line in infile:
                line = line.rstrip()
                print(line)
                query = f'SELECT rowid,{table[:-1]},{column} FROM "{table}" WHERE {table[:-1]} LIKE "%{line}%"'
                #print(query)
                rows = self.query(query)
                for row in rows:
                    print(f'TO DELETE {row}')
                query = f'DELETE FROM "{table}" WHERE {table[:-1]} LIKE "%{line}%"'
                self.query(query)
        self.output("End of remove rows which contains defined strings")

    def remove_empty(self,table,column):
        self.output("Start to remove empty rows")
        query = f'SELECT rowid,{table[:-1]},{column} FROM "{table}" WHERE {column} IS NULL ORDER BY rowid'
        rows = self.query(query)
        for row in rows:
            print(f'TO DELETE {row}')
        query = f'DELETE FROM {table} WHERE {column} IS NULL'
        # print(query)
        result = self.query(query)
        print(result)
        self.output("End of remove empty rows")

    def module_run(self):
        # handle the source of information for the report
        table = self.options['table']
        column = self.options['column']

        query = f'SELECT COUNT(rowid) FROM {table}'
        count = self.query(query)
        self.output(f'There are {count[0][0]} rows in table {table}')
        self.output("Start deduplication")

        # Optional: remove rows with empty data in column
        if self.options['nulls']:
            self.remove_empty(table,column)

        # Optional: remove rows with defined strings in name
        if self.options['filename']:
            self.remove_special(table,column,self.options['filename'])

        # Query to select distinct items
        query = f'SELECT DISTINCT {table[:-1]},{column} FROM "{table}" ORDER BY "{table[:-1]}"'
        #self.output(query)
        rows = self.query(query)
        for row in rows:
            #print(row)
            self.deduplicate(table,column,row)
            #print(f'{table[:-1]}:{row[0]}, {column}:{row[1]}')
        #self.output(f"{len(rows)} distinct items found in '{table}'.")
        self.output("End deduplication")
        query = f'SELECT COUNT(rowid) FROM {table}'
        count = self.query(query)
        self.output(f'There are {count[0][0]} rows in table {table}')
