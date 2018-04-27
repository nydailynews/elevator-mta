#!/usr/bin/env python
# Download and log the MTA's status updates. We only log changes.
from __future__ import print_function
import argparse
import doctest
import json
import os, sys
from datetime import datetime, timedelta

#from filewrapper import FileWrapper
#from sqliter import Storage
import dicts

class Logger:
    """ We're logging ...
        """

    def __init__(self, *args, **kwargs):
        """
            >>> args = build_parser([])
            >>> log = Logger(args)
            """
        # Get the results from the last time we ran this.
        try:
            fh = open('_output/active.json', 'rb')
            self.previous = json.load(fh)
            fh.close()
        except:
            self.previous = None

        self.args = []
        if len(args) > 0:
            self.args = args[0]
        self.db = Storage('mta-ele')
        self.double_check = { 'in_text': 0, 'objects': 0 }
        self.new = { 'subway': {
            'starts': dict(zip(dicts.lines['elevators'], ([] for i in range(len(dicts.lines['elevators']))))),
            'stops': dict(zip(dicts.lines['elevators'], ([] for i in range(len(dicts.lines['elevators'])))))
            }
        }

    def parse_html(self):
        """
            Turn the table that contains the out of service elevator data. Returns a dict.
            >>> args = build_parser([])
            >>> log = Logger(args)
            >>> log.get_files(['test.html'])
            ['test.html']
            >>> d = log.parse_html('test.html')
            """
        pass

    def get_files(self, files_from_args):
        """
            >>> args = build_parser([])
            >>> log = Logger(args)
            >>> log.get_files(['test.html'])
            ['test.html']
            """
        if files_from_args == []:
            # If we didn't pass any arguments to logger, we download the current HTML
            rando = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
            url = 'http://advisory.mtanyct.info/EEoutage/EEOutageReport.aspx?StationID=All&%s' % rando
            fh = FileWrapper('_input/mta.html')
            fh.open()
            try:
                fh.write(fh.request(url))
            except:
                fh.write(fh.request(url))
            fh.close()
            files = ['mta.html']
        else:
            files = files_from_args
            if '*' in files[0]:
                # Wildcard matching on filenames so we can process entire directories
                # put example of that here.
                pass
            if files[0][-1] == '/':
                # If the arg ends with a forward slash that means it's a dir
                files = os.listdir(files[0])
        return files

def main(args):
    """ There are two situations we run this from the command line: 
        1. When building archives from previous day's service alerts and
        2. When keeping tabs on the current days's service alerts.

        Most of what we do here for each is the same, but with #2 we only
        process one file, and we have to look up stored information to ensure
        the intervals values are current.
        >>> args = build_parser([])
        >>> main(args)
        """
    log = Logger(args)
    if args.initial:
        log.initialize_db()

    if args.reset_table:
        tables = log.db.q.get_tables()
        if args.verbose:
            print("NOTICE: We are resetting the %s table (amongst %s)" % (args.reset_table, tables.__str__()))
        #if args.reset_table in tables:
        log.db.setup(args.reset_table)

    files = log.get_files(args.files)

    for fn in files:
        lines = log.parse_file(fn)

    commit_count = log.commit_starts(lines)
    commit_count += log.commit_stops()
    log.db.conn.commit()

    log.write_json('current')
    log.write_json('active')
    params = { 'date': datetime.now().date().__str__() }
    log.write_json('archive', **params)

    if args.verbose:
        print("NOTICE: ", log.double_check)
        print("NOTICE: ", log.new['subway']['starts'].values())
        print("NOTICE: ", log.new['subway']['stops'].values())

    #new_len = sum(len(v) for v in log.new['subway']['starts'].itervalues()) + sum(len(v) for v in log.new['subway']['stops'].itervalues())

    if commit_count > 0 and log.double_check['in_text'] != log.double_check['objects']:
        log.save_xml()

    log.db.conn.close()


def build_parser(args):
    """ This method allows us to test the args.
        >>> args = build_parser(['--verbose'])
        >>> print(args.verbose))
        True
        """
    parser = argparse.ArgumentParser(usage='$ python logger.py',
                                     description='Get the latest MTA elevator outages and add any new ones.',
                                     epilog='Example use: python logger.py')
    parser.add_argument("-i", "--initial", dest="initial", default=False, action="store_true")
    parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true")
    parser.add_argument("--test", dest="test", default=False, action="store_true")
    parser.add_argument("files", nargs="*", help="Path to files to ingest manually")
    parser.add_argument("--reset_table", dest="reset_table", default=False, help="Truncate and create a table in the database")
    args = parser.parse_args(args)
    return args


if __name__ == '__main__':
    args = build_parser(sys.argv[1:])

    if args.test:
        doctest.testmod(verbose=args.verbose)
    main(args)
