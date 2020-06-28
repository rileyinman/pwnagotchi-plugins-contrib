import json
import logging
import os
import subprocess
from threading import Lock

import pwnagotchi.plugins as plugins
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts


class hashie(plugins.Plugin):
    __author__ = 'junohea.mail@gmail.com'
    __version__ = '1.0.1'
    __license__ = 'GPL3'
    __description__ = '''
                        Attempt to automatically convert pcaps to a crackable format.
                        If successful, the files  containing the hashes will be saved
                        in the same folder as the handshakes.
                        The files are saved in their respective Hashcat format:
                          - EAPOL hashes are saved as *.2500
                          - PMKID hashes are saved as *.16800
                        All PCAP files without enough information to create a hash are
                          stored in a file that can be read by the webgpsmap plugin.

                        Why use it?:
                          - Automatically convert handshakes to crackable formats!
                              We dont all upload our hashes online ;)
                          - Repair PMKID handshakes that hcxpcaptool misses
                          - If running at time of handshake capture, on_handshake can
                              be used to improve the chance of the repair succeeding
                          - Be a completionist! Not enough packets captured to crack a network?
                              This generates an output file for the webgpsmap plugin, use the
                              location data to revisit networks you need more packets for!

                        Additional information:
                          - Currently requires hcxpcaptool compiled and installed
                          - Attempts to repair PMKID hashes when hcxpcaptool cant find the SSID
                            - hcxpcaptool sometimes has trouble extracting the SSID, so we
                                use the raw 16800 output and attempt to retrieve the SSID via tcpdump
                            - When access_point data is available (on_handshake), we leverage
                                the reported AP name and MAC to complete the hash
                            - The repair is very basic and could certainly be improved!
                        Todo:
                          Make it so users dont need hcxpcaptool (unless it gets added to the base image)
                              Phase 1: Extract/construct 2500/16800 hashes through tcpdump commands
                              Phase 2: Extract/construct 2500/16800 hashes entirely in python
                          Improve the code, a lot
                        '''

    def __init__(self):
        logging.info("[hashie] Plugin loaded.")
        self.lock = Lock()

    # called when everything is ready and the main loop is about to start
    def on_config_changed(self, config):
        handshake_dir = config['bettercap']['handshakes']

        if 'interval' not in self.options or not (self.status.newer_then_hours(self.options['interval'])):
            logging.info('[hashie] Starting batch conversion of pcap files...')
            with self.lock:
                self._process_stale_pcaps(handshake_dir)

    def on_handshake(self, agent, filename, access_point, client_station):
        with self.lock:
            handshake_status = []
            fullpathNoExt = filename.split('.')[0]
            name = filename.split('/')[-1:][0].split('.')[0]

            if os.path.isfile(f'{fullpathNoExt}.2500'):
                handshake_status.append(f'Already have {name}.2500 (EAPOL)')
            elif self._writeEAPOL(filename):
                handshake_status.append(f'Created {name}.2500 (EAPOL) from pcap')

            if os.path.isfile(f'{fullpathNoExt}.16800'):
                handshake_status.append(f'Already have {name}.16800 (PMKID)')
            elif self._writePMKID(filename, access_point):
                handshake_status.append(f'Created {name}.16800 (PMKID) from pcap')

            if handshake_status:
                logging.info('[hashie] Good news:\n\t' + '\n\t'.join(handshake_status))

    def _writeEAPOL(self, fullpath):
        fullpathNoExt = fullpath.split('.')[0]
        filename = fullpath.split('/')[-1:][0].split('.')[0]
        result = subprocess.getoutput(f'hcxpcaptool -o {fullpathNoExt}.2500 {fullpath} >/dev/null 2>&1')

        if os.path.isfile(f'{fullpathNoExt}.2500'):
            logging.debug(f'[hashie] [+] EAPOL Success: {filename}.2500 created.')
            return True

        return False

    def _writePMKID(self, fullpath, apJSON):
        fullpathNoExt = fullpath.split('.')[0]
        filename = fullpath.split('/')[-1:][0].split('.')[0]
        result = subprocess.getoutput(f'hcxpcaptool -k {fullpathNoExt}.16800 {fullpath} >/dev/null 2>&1')
        if os.path.isfile(f'{fullpathNoExt}.16800'):
            logging.debug(f'[hashie] [+] PMKID Success: {filename}.16800 created.')
            return True

        #make a raw dump
        result = subprocess.getoutput(f'hcxpcaptool -K {fullpathNoExt}.16800 {fullpath} >/dev/null 2>&1')
        if os.path.isfile(f'{fullpathNoExt}.16800'):
            if not self._repairPMKID(fullpath, apJSON):
                logging.debug(f'[hashie] [-] PMKID Fail: {filename}.16800 could not be repaired.')
                return False

            logging.debug(f'[hashie] [+] PMKID Success: {filename}.16800 repaired.')
            return True

        logging.debug(f'[hashie] [-] Could not attempt repair of {filename} as no raw PMKID file was created.')
        return False

    def _repairPMKID(self, fullpath, apJSON):
        hashString = ""
        clientString = []
        fullpathNoExt = fullpath.split('.')[0]
        filename = fullpath.split('/')[-1:][0].split('.')[0]
        logging.debug(f'[hashie] Repairing {filename}...')
        with open(f'{fullpathNoExt}.16800', 'r') as tempFileA:
            hashString = tempFileA.read()
        if apJSON != "":
            clientString.append(f"{apJSON['mac'].replace(':', '')}:{apJSON['hostname'].encode('hex')}")
        else:
            #attempt to extract the AP's name via hcxpcaptool
            result = subprocess.getoutput(f'hcxpcaptool -X /tmp/{filename} {fullpath} >/dev/null 2>&1')
            if os.path.isfile(f'/tmp/{filename}'):
                with open(f'/tmp/{filename}', 'r') as tempFileB:
                    temp = tempFileB.read().splitlines()
                    for line in temp:
                        clientString.append(line.split(':')[0] + ':' + line.split(':')[1].strip('\n').encode().hex())
                os.remove(f'/tmp/{filename}')
            #attempt to extract the AP's name via tcpdump
            tcpCatOut = subprocess.check_output("tcpdump -ennr " + fullpath  + " \"(type mgt subtype beacon) || (type mgt subtype probe-resp) || (type mgt subtype reassoc-resp) || (type mgt subtype assoc-req)\" 2>/dev/null | sed -E 's/.*BSSID:([0-9a-fA-F:]{17}).*\\((.*)\\).*/\\1\t\\2/g'", shell=True).decode('utf-8')
            if ":" in tcpCatOut:
                for i in tcpCatOut.split('\n'):
                    if ":" in i:
                        clientString.append(i.split('\t')[0].replace(':', '') + ':' + i.split('\t')[1].strip('\n').encode().hex())
        if clientString:
            for line in clientString:
                if line.split(':')[0] == hashString.split(':')[1]: #if the AP MAC pulled from the JSON or tcpdump output matches the AP MAC in the raw 16800 output
                    hashString = hashString.strip('\n') + ':' + (line.split(':')[1])
                    if (len(hashString.split(':')) == 4) and not hashString.endswith(':'):
                        with open(f"{fullpath.split('.')[0]}.16800", 'w') as tempFileC:
                            logging.debug(f'[hashie] Repaired: {filename} ({hashString}).')
                            tempFileC.write(f'{hashString}\n')
                        return True

                    logging.debug(f'[hashie] Discarded: {line} {hashString}.')
        else:
            os.remove(f"{fullpath.split('.')[0]}.16800")
            return False

    def _process_stale_pcaps(self, handshake_dir):
        handshakes_list = [os.path.join(handshake_dir, filename) for filename in os.listdir(handshake_dir) if filename.endswith('.pcap')]
        failed_jobs = []
        successful_jobs = []
        lonely_pcaps = []
        for num, handshake in enumerate(handshakes_list):
            fullpathNoExt = handshake.split('.')[0]
            pcapFileName = handshake.split('/')[-1:][0]
            if not os.path.isfile(f'{fullpathNoExt}.2500'): #if no 2500, try
                if self._writeEAPOL(handshake):
                    successful_jobs.append(f'2500: {pcapFileName}')
                else:
                    failed_jobs.append(f'2500: {pcapFileName}')
            if not os.path.isfile(f'{fullpathNoExt}.16800'): #if no 16800, try
                if self._writePMKID(handshake, ""):
                    successful_jobs.append(f'16800: {pcapFileName}')
                else:
                    failed_jobs.append(f'16800: {pcapFileName}')
                    if not os.path.isfile(f'{fullpathNoExt}.2500'): #if no 16800 AND no 2500
                        lonely_pcaps.append(handshake)
                        logging.debug(f'[hashie] Batch job: added {pcapFileName} to lonely list.')
            if ((num + 1) % 50 == 0) or (num + 1 == len(handshakes_list)): #report progress every 50, or when done
                logging.info(f'[hashie] Batch job: {num + 1}/{len(handshakes_list)} done ({len(lonely_pcaps)} fails).')
        if successful_jobs:
            logging.info(f'[hashie] Batch job: {len(successful_jobs)} new handshake files created.')
        if lonely_pcaps:
            logging.info(f'[hashie] Batch job: {len(lonely_pcaps)} networks without enough packets to create a hash.')
            self._getLocations(lonely_pcaps)

    def _getLocations(self, lonely_pcaps):
        #export a file for webgpsmap to load
        with open('/root/.incompletePcaps', 'w') as isIncomplete:
            count = 0
            for pcapFile in lonely_pcaps:
                filename = pcapFile.split('/')[-1:][0] #keep extension
                fullpathNoExt = pcapFile.split('.')[0]
                isIncomplete.write(f'{filename}\n')
                if os.path.isfile(f'{fullpathNoExt}.gps.json') or os.path.isfile(f'{fullpathNoExt}.geo.json') or os.path.isfile(f'{fullpathNoExt}.paw-gps.json'):
                    count += 1
            if count != 0:
                logging.info(f'[hashie] Used {str(count)} GPS/GEO/PAW-GPS files to find lonely networks, go check webgpsmap! ;)')
            else:
                logging.info('[hashie] Could not find any GPS/GEO/PAW-GPS files for the lonely networks.')

    def _getLocationsCSV(self, lonely_pcaps):
        #in case we need this later, export locations manually to CSV file, needs try/catch/paw-gps format/etc.
        locations = []
        for pcapFile in lonely_pcaps:
            filename = pcapFile.split('/')[-1:][0].split('.')[0]
            fullpathNoExt = pcapFile.split('.')[0]
            if os.path.isfile(f'{fullpathNoExt}.gps.json'):
                with open(f'{fullpathNoExt}.gps.json', 'r') as tempFileA:
                    data = json.load(tempFileA)
                    locations.append(f"{filename},{str(data['Latitude'])},{str(data['Longitude'])},50")
            elif os.path.isfile(f'{fullpathNoExt}.geo.json'):
                with open(f'{fullpathNoExt}.geo.json', 'r') as tempFileB:
                    data = json.load(tempFileB)
                    locations.append(f"{filename},{str(data['location']['lat'])},{str(data['location']['lng'])},{str(data['accuracy'])}")
            elif os.path.isfile(f'{fullpathNoExt}.paw-gps.json'):
                with open(f'{fullpathNoExt}.paw-gps.json', 'r') as tempFileC:
                    data = json.load(tempFileC)
                    locations.append(f"{filename},{str(data['lat'])},{str(data['long'])},50")
        if locations:
            with open('/root/locations.csv', 'w') as tempFileD:
                for loc in locations:
                    tempFileD.write(f'{loc}\n')
            logging.info(f'[hashie] Used {len(locations)} GPS/GEO files to find lonely networks, load /root/locations.csv into a mapping app and go say hi!')
