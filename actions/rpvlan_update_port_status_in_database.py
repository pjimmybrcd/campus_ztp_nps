from st2actions.runners.pythonrunner import Action
from lib import actions
import pymysql.cursors

class RpvlanUpdateMacAuthFailureDatabaseAction(actions.SessionAction):
  def __init__(self,config):
     super(RpvlanUpdateMacAuthFailureDatabaseAction, self).__init__(config)

  def run(self, timestamp, switch_name, ip, ap_name, port, action):

     if action=='add':
         self.process_add_port(timestamp, switch_name, ip, ap_name, port)

     if action=='remove':
         self.process_remove_port(timestamp, switch_name, ip, ap_name, port)

     # TODO: Report errors like database failure!
     return (True)

  def process_add_port(self, timestamp, switch_name, ip, ap_name, port):
        """
        connection = pymysql.connect(
             host=self._db_addr, 
             user=self._db_user,      
             passwd=self._db_pass,  
             db=self._db_name)

        cursor = connection.cursor()
        sql = "update authorized set ip='NULL', port='NULL', switch_name='NULL', timestamp='NULL' where port='%s' and ip='%s'" % (port, ip)
        cursor.execute(sql)
        connection.commit()
        connection.close()
        """

  def process_remove_port(self, timestamp, switch_name, ip, ap_name, port):
        connection = pymysql.connect(
             host=self._db_addr, 
             user=self._db_user,      
             passwd=self._db_pass,  
             db=self._db_name)
        
        cursor = connection.cursor()
        sql = "update authorized set ip='NULL', port='NULL', switch_name='NULL', timestamp='NULL' where port='%s' and ip='%s'" % (port, ip)
        cursor.execute(sql)

	sql = "delete from failures where port='%s' and ip='%s'" % (port, ip)
        cursor.execute(sql)
        cursor.close()
        connection.commit()
        connection.close()

