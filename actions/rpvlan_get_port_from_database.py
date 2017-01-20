from st2actions.runners.pythonrunner import Action

import pymysql.cursors
import json,sys

class RpvlanGetPortForMacFromDatabaseAction(Action):
  def __init__(self,config):
     super(RpvlanGetPortForMacFromDatabaseAction, self).__init__(config)

  def run(self,mac):

     return self.get_port_for_mac(mac)

     # TODO: Report errors like database failure!

  def get_port_for_mac(self,mac):

        connection = pymysql.connect(
             host="10.0.0.43", 
             user="nps_remote",      
             passwd="password",  
             db='nps')        

        with connection.cursor() as cursor:
            # TODO: Check if mac is already in database and see if it's moved, etc
            # Write failed mac to database
            sql = "select device,port from failed_mac_locations where mac='%s'" % mac
            cursor.execute(sql)
            results = cursor.fetchone()
            if results:
                sys.stdout.write(results[0])
        	connection.close()
		return (True, results[1])

            connection.close()
	    return (False,'Mac Address Not Found!')

