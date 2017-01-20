from st2actions.runners.pythonrunner import Action
from lib import actions
import pymysql.cursors
import json

class RpvlanUpdateMacAuthFailureDatabaseAction(actions.SessionAction):
  def __init__(self,config):
     super(RpvlanUpdateMacAuthFailureDatabaseAction, self).__init__(config)

  def run(self, timestamp, switch_name, ip, ap_name, mac, port):

     self.process_mac_failure(timestamp, switch_name, ip, ap_name, port, mac)

     # TODO: Report errors like database failure!
     return (True)

  def process_mac_failure(self, timestamp, switch_name, ip, ap_name, port, mac):

        connection = pymysql.connect(
             host=self._db_addr, 
             user=self._db_user,      
             passwd=self._db_pass,  
             db=self._db_name)       

	#Update row.
	cursor = connection.cursor()
        sql = "update authorized set timestamp='%s', switch_name='%s', ip='%s', device='%s', port='%s' where mac='%s'" % (timestamp, switch_name, ip, ap_name, port, mac)
        cursor.execute(sql)
        connection.commit()
        cursor.close()
        connection.close()

