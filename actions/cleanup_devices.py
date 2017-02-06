import json
from lib import actions, Excel_Reader, ztp_utils
import openpyxl
import pymysql
import re
import logging
from logging.handlers import RotatingFileHandler

class GetInventoryAction(actions.SessionAction):
    def __init__(self, config):
        super(GetInventoryAction, self).__init__(config)

        self._logger = logging.getLogger('cleanup_logger')
	self._logger.setLevel(logging.DEBUG)
        self._fileHandler = RotatingFileHandler("/var/log/cleanuplog_bwc", mode='w', maxBytes=10*1024*1024, backupCount=2, encoding=None, delay=0)
        self._fileHandler.setLevel(logging.DEBUG)
        self._logger.addHandler(self._fileHandler)

        self._connection = pymysql.connect(
                  host=self._db_addr, 
                  user=self._db_user,      
                  passwd=self._db_pass,  
                  db=self._db_name)
        self._cursor =  self._connection.cursor()

        #Regex for IP Address
        self._ip_addr_regex = re.compile('(\d+\.\d+\.\d+\.\d+)')
        #Regex for port ex: 1/1/27
        self._port_regex = re.compile('(\d+\/\d+\/\d+)')
        #Regex for ICX Output: "2cc5.d321.b3b3 1/1/23    Dynamic   233"
        self._icx_output_regex = re.compile('([0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})?(\s*)(\s\d+\/\d+\/\d+)(\s*)(Dynamic)(\s*)(233)')

    def run(self, filepath, sheetname, ip_column_name, switch_name_column_name):
        status = self.clean(filepath, sheetname, ip_column_name, switch_name_column_name)
        self._cursor.close()
        self._connection.commit()
        self._connection.close()
        return status

    def clean(self, filepath, sheetname, ip_column_name, switch_name_column_name):
        self._logger.info("***** Cleanup Action Initiated *****")
        wb = openpyxl.load_workbook(filepath, data_only=True)
        ws = wb.get_sheet_by_name(sheetname)

        ip_index = -1
        name_index = -1
        for row in ws.iter_rows():
                for index, cell in enumerate(row):
                        if(str(cell.value)==ip_column_name):
                                ip_index = index
                        if(str(cell.value)==switch_name_column_name):
                                name_index = index
                break

        print("IP Address Column Index: " + str(ip_index), "Switch Name Column Index: " + str(name_index))

        for row in ws.iter_rows(row_offset=1):
               ip, name = "NULL", "NULL"
               for index, cell in enumerate(row):
                       if index == ip_index and cell.value!=None:
                               ip = cell.value
                       if index == name_index and cell.value!=None:
                               name = cell.value

               if(self._ip_addr_regex.match(ip)==None or name=="NULL"):
                       self._logger.info("Error Invalid IP Address in file or invalid name, IP: '%s' and Name:'%s'" % (ip, name))
                       continue

               self.start_icx_session(ip, name)

    def start_icx_session(self, ip, name):
        command = "show mac-address | inc 233"
        self._logger.info("Starting cleanup for ICX switch with ip: '%s' and name: '%s'" % (ip, name))
        icx_session = ztp_utils.start_session(ip, self._username, self._password,
                                              self._enable_username, self._enable_password, "ssh")
        (success, output) = ztp_utils.send_commands_to_session(icx_session, command, False)
        if(success == False):
                self._logger.info("Error in send Command: '%s' for Device: '%s', Results: '%s', '%s'." % (command, ip, success, output))
                return
        self.parse_output(icx_session, ip, name, output)


    def parse_output(self, icx_session, switch_ip, switch_name, output):
        self._logger.info("Parsing output for ICX switch name: '%s', switch IP: '%s'" % (switch_name, switch_ip))
        self._logger.info("Output: '%s'" % (output))
        lines = output.splitlines()
        for line in lines:
               match = self._icx_output_regex.match(line.strip())
               if match:
                       self._logger.info("Regex successful match for output line: '%s'" % (line))
                       self.verify_and_update(icx_session, switch_ip, switch_name, match.group(1).strip(), match.group(3).strip())
               else:
                       self._logger.info("Regex failed match for output line: '%s'" % (line))
        
    def verify_and_update(self, icx_session, switch_ip, switch_name, mac, port):
        self._logger.info("Verifying and updating db for ICX Switch IP: '%s', AP MAC address: '%s', ICX port: '%s'" % (switch_ip, mac, port))
        sql = "select count(*) from authorized where mac='%s'" % (mac)
        self._cursor.execute(sql)
        count = self._cursor.fetchone()[0]
        if count==0:
               #Mac address is not in the database so don't do anything.
               self._logger.info("Warning AP MAC address not in database for AP MAC: '%s', on ICX port: '%s', on ICX IP:'%s'" % (mac, port, switch_ip))
               return
        else:
               #Mac Address was found
               self._logger.info("Mac address found in database for AP MAC: '%s'" % (mac))

        sql = "select ip, port, base_mac, ap_name, switch_name from authorized where mac='%s'" % (mac)
        self._cursor.execute(sql)
        row = self._cursor.fetchone()
        db_ip = row[0]
        db_port = row[1]
        db_base_mac = row[2]
        db_ap_name = row[3]
        db_switch_name = row[4]
        
        if(self._ip_addr_regex.match(db_ip)==None or self._port_regex.match(db_port)==None or db_switch_name=="NULL"):
               self._logger.info("Warning Database was missing information for AP MAC:'%s'." % (mac))
               sql = "update authorized set ip='%s', port='%s' where mac='%s'" % (address, port, mac)
               self._cursor.execute(sql)
               self._logger.info("Database updated for AP MAC:'%s'." % (mac))
        elif(db_ip!=switch_ip or db_port!=port or db_switch_name!=switch_name):
               self._logger.info("Warning Database had invalid information for AP MAC:'%s'." % (mac))
               self._logger.info("Warning Database Information: Switch IP: '%s', Switch Name: '%s', Switch Port: '%s' for device with MAC: '%s'" % (db_ip, db_switch_name, db_port, mac))
               self._logger.info("Warning Switch Information: Switch IP: '%s', Switch IP: '%s', Switch Port: '%s' for device with MAC: '%s'" % (switch_ip, switch_name, port, mac))
        else:
               self._logger.info("Database information for AP MAC: '%s' is up-to-date." % (mac))

        self._connection.commit()

        #Updates the port name on the ICX
        self.icx_port_name_update(icx_session, port, db_ap_name)

        #Updates the name on the ruckus controller
        self.ruckus_controller_update(switch_ip, switch_name, db_base_mac, db_ap_name, port)

    def icx_port_name_update(self, icx_session, port, ap_name):
        self._logger.info("Updating ICX Port Name to be: '%s' for port: '%s'" % (ap_name, port))
        icx_port_name_command = "interface ethernet '%s';port-name '%s';" % (port, ap_name)
        (success, output) = ztp_utils.send_commands_to_session(icx_session, icx_port_name_command, True)
        self._logger.info("ICX Port Naming Result: '%s', Output: '%s'" % (success, output))

    """
    # Not needed currently.
    def icx_port_down_update(self, icx_session, port, ap_name=""):
        self._logger.info("Performing port down operation.")
        icx_port_down_command = "authentication;dot1x enable ethernet '%s';mac-authentication enable ethernet '%s';interface ethernet '%s';no dual-mode 233;no authentication auth-default-vlan 233;dot1x port-control auto;no port-name '%s';vlan 233;no tagged ethernet '%s'" % (port, port, port, ap_name, port)
        (success, output) = ztp_utils.send_commands_to_session(icx_session, icx_port_name_command, True)
        self._logger.info("ICX Port Down Result: '%s', Output: '%s'" % (success, output))
    """

    def ruckus_controller_update(self, switch_ip, switch_name, base_mac, ap_name, port):
        ruckus_command = "ap '%s';name \"'%s' '%s'\";description \"'%s' '%s' '%s' '%s\";end" % (base_mac, ap_name, switch_name, ap_name, switch_name, switch_ip, port)
        if(self._ruckus_controller_ip != None):
               ruckus_session = ztp_utils.ruckus_controller_start_session(self._ruckus_controller_ip,
                                                self._ruckus_controller_username,
						self._ruckus_controller_password,
						self._ruckus_controller_enable_username,
						self._ruckus_controller_enable_password, "ssh")
               (success, output) = ztp_utils.send_commands_to_session(ruckus_session, ruckus_command, False)
               self._logger.info("Ruckus Controller Naming Result: '%s', Output: '%s'" % (success, output))
               
