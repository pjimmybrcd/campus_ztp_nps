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

        #Remove the mac addr tuple in table may not be in there but it's fine
	cursor = connection.cursor()
	sql = "delete from failures where mac='%s'" % (mac)
        cursor.execute(sql)
        connection.commit()
	cursor.close()

	#Insert new row.
	cursor = connection.cursor()
        sql = "insert into failures (timestamp, switch_name, ip, mac, device, port) values('%s', '%s', '%s','%s','%s','%s')" % (timestamp, switch_name, ip, mac, ap_name, port)
        cursor.execute(sql)
        connection.commit()
        cursor.close()
        connection.close()

