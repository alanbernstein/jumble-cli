#!/usr/bin/python
"""backend for jumble app, handle retrieving and caching to file
the source used by http://www.chicagotribune.com/chi-jumbleclassic-htmlpage-htmlstory.html
"""
from datetime import datetime as dt
import xml.etree.ElementTree as ET
import os
import json
import urllib2
import cgitb


cgitb.enable(format='text')
print("Content-Type: text/plain;charset=utf-8")
print("")


# only need one method - get latest
# - run on a daily cron, and cache the result
# - retrieve from cache
# - JumbleClient, unchanged, handles both

def main():
    # env = os.environ
    # url = env['REQUEST_URI']
    # params = urlparse.parse_qs(urlparse.urlparse(url).query)

    # TODO: allow requesting old data, either with date string or day-delta
    #       jumble.py?date=161127
    #       jumble.py?prev=1
    # TODO: move common to separate file

    jc = JumbleClient()
    jumble = jc.get_jumble()
    print(json.dumps(jumble))


class JumbleClient(object):
    base_url = 'https://www.uclick.com/puzzles/tmjmf/puzzles/tmjmf'
    date_format = '%y%m%d'
    #cachefile_base = '/home/alanb0/public_html/data/jumble/'
    cachefile_base = '/Users/abernstein/.cache/jumble/'

    def __init__(self):
        if not os.path.isdir(self.cachefile_base):
            os.makedirs(self.cachefile_base)

    def get_jumble(self, date=None):
        """public interface"""
        if not date:
            date = dt.today()

        jumble_xml = self.get_jumble_from_server_or_cache(date)
        jumble_json = self.parse_jumble_xml(jumble_xml)
        jumble_json['local_image'] = self.get_local_filename(date, 'gif')
        return jumble_json

    def parse_jumble_xml(self, xml_string):
        if 'xml' not in xml_string:
            # not sure why this happens
            raise Exception('request error')

        root = ET.fromstring(xml_string)
        layout_original = root.find('solution')[0].attrib['layout'],
        if type(layout_original) == tuple:
            layout_original = layout_original[0]
        return {
            'date': root.find('Date').attrib['v'],
            'clues': [self.parse_clue(c) for c in root.find('clues')],
            'caption': root.find('caption')[0].attrib['t'],
            'layout_original': layout_original,
            'layout': get_layout_display(layout_original),
            'answer': root.find('solution')[0].attrib['a'],
        }

    def parse_clue(self, xml_clue):
        return {
            'jumbled': xml_clue.attrib['j'],
            'answer': xml_clue.attrib['a'],
            'circles': [int(n) for n in xml_clue.attrib['circle'].split(',')],
        }

    def get_local_filename(self, date, ext):
        return '%s%s.%s' % (self.cachefile_base, dt.strftime(date, self.date_format), ext)

    def get_jumble_from_server_or_cache(self, date):
        # filename = '%s%s.xml' % (self.cachefile_base, dt.strftime(date, self.date_format))
        xml_filename = self.get_local_filename(date, 'xml')
        gif_filename = self.get_local_filename(date, 'gif')

        if os.path.isfile(xml_filename):
            with open(xml_filename, 'r') as f:
                xml = f.read()
            # print('read jumble cache (%s)' % filename)
            return xml
        else:
            xml = self.get_jumble_from_server(date)
            gif = self.get_jumble_from_server(date, 'gif')
            with open(xml_filename, 'w') as f:
                f.write(xml)
            with open(gif_filename, 'wb') as f:
                f.write(gif)

            linkname = '%slatest.xml' % self.cachefile_base
            try:
                os.unlink(linkname)
                # print('unlink %s' % linkname)
            except:
                pass
            try:
                os.symlink(xml_filename, linkname)
                # print('link %s' % filename)
            except:
                pass
            # print('wrote to cache (%s)' % filename)
            return xml

    def get_jumble_from_server(self, date, ext='xml'):
        suffix = '-data' if ext == 'xml' else ''
        url = '%s%s%s.%s' % (self.base_url, dt.strftime(date, self.date_format), suffix, ext)
        print('getting jumble from server (%s)' % url)
        resp = urllib2.urlopen(url)
        return resp.read()


def get_layout_display(layout):
    """
    needs to be parsed:
    'OUT{ TO }PASTURE' -> solution = OUTPASTURE, display = "___ TO _______"
    just use state machine to track whether inside parens
    """
    # too naive:
    # s1 = re.sub('[A-Z]', '_', layout)
    # s2 = re.sub('[{}]', '', s1)

    disp = ''
    state = 0
    for c in layout:
        if c == '{':
            state = 1
        elif c == '}':
            state = 0
        elif state == 0 and c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            disp += '_'
        else:
            disp += c
    return disp


if __name__ == '__main__':
    main()
