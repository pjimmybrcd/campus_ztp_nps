# Using SDN to auto-connect Ruckus APs to Brocade ICX switches  
This integration pack works with Brocade Workflow Composer (BWC) to enhance Zero Touch Provisioning (ZTP) to reliably setup ICX campus access Ethernet switches.

BWC is a platform for integration and automation across services and tools. It ties together your existing infrastructure and application environment so you can more easily automate that environment. It has a particular focus on taking actions in response to events.

Speed up deployment with automation using Brocade’s Workflow Composer (BWC).

As you update your wireless network with new access points (AP), you must plan out your deployment.  Deployment can take for days to weeks as it requires a technician to log into every switch and configure it to support the new AP.  This configuration becomes more complicated when you are using Dot1x and MAC-AUTH to validate a device prior to access to the network.

When deploying Ruckus APs in a Brocade ICX network, Brocade’s Workflow Composer (BWC) simplifies the problem.  Deployment becomes seconds instead of days.  BWC uses information provided by the Brocade switch to automatically insert the Ruckus AP in a Dot1x and MAC-AUTH environment, while ensuring that a random device is not allowed on the network.

The following pack piggy backs off of the Campus ZTP Integration Pack available online on GitHub.
https://github.com/tbrawly/campus_ztp

## Overview
As a Ruckus AP is plugged into a Brocade ICX, it triggers a Dot1x and MAC-AUTH sequence that will fail.  Upon authentication failure, the ICX forwards a syslog message to BWC containing the AP's mac address and the Ethernet port.  BWC monitors the syslog file to determine whether the message is an authentication failure and the mac matches a valid Ruckus AP. If so, a BWC trigger will be set, and a rule matched initiating a workflow to reconfigure the ICX switch.

In our solution, the ICX is configured with a restricted-vlan and "auth-fail-action restricted-vlan" configured.  Devices that pass authentication are placed into the auth-default-vlan and allowed onto the corporate; however, devices that fail authentication are moved to the restricted-vlan.

When the Ruckus AP is connected to the ICX switch and powers up, the ICX tries to authenticate the AP's mac address with the Radius server (MAC_AUTH), where is it denied access.

When the ICX receives information from authorization failure message from the Radius server, it forwards the syslog message to BWC.  BWC reads the syslog message looking for these specific messages.

	Example Syslog:
		"Jan 1 07:26:35 ZTP_Campus_ICX7750 172.20.40.243 MACAUTH: Port 1/1/48 Mac 406c.8f38.4fb7 - authentication failed since RADIUS server rejected"
		"Jan  4 14:00:49 ING-135-01 172.20.41.44 MAC Authentication failed for [EC8C.A225.B280 ] on port 1/1/36 (Invalid User)"

When the syslog is matched with the format above, the MAC address from the message is compared to a list of authorized MACs stored in the database. If the MAC from the log matches a MAC address stored in the database of authorized addresses, the device name is retrieved from the database and an action chain is issued. This action chain first changes the configuration on the switch then updates the information in the database storing the location of the AP on the network. The configuration change is done by sending a template to the switch via a SSH connection.


If the MAC address from the syslog is not found in the database, meaning that the device is unauthorized, the information will be stored in a failures table in the database for future reference or additional actions for non-Ruckus AP devices.

Once the AP is in the production wireless VLAN, it retrieves an IP address by DHCP is able to reach the Virtual SmartZone (vSZ) Controller network.  Here it will receive its configuration information.


For added security, the network must ensure that if the Ruckus AP is removed or the port disabled, the configuration of that port on the ICX switch will be reverted back to the initial configuration and database entry removed. Simply enabling the port or re-installing the AP, will just restart the process.

	Example Syslog:
		"Dec 19 17:10:17 RSOC-TEST-STACK 172.20.40.243 System: Interface ethernet 2/1/29, state down"

When a syslog is matched with the format above, the BWC sensor will check to see if the port on the switch was authorized for a Ruckus AP, meaning that it checks to see if the initial configuration of the port was changed to allow an authorized device to connect. If the configuration was changed, then a template that reverse the changes will be sent to the switch via SSH. Upon successful completion, the information in the database will be updated.

Currently, this port down feature is disabled, but can be reenabled by modifying the sensor.

## Getting Started
The following information is a quick start guide on how to get this pack up and running along with BWC.

## Prereqs:
1. Brocade Workflow Composer (BWC)
2. MySQL Server
3. Rsyslog

## Prerequisites Installation
### Install BWC
		curl -sSL -O https://brocade.com/bwc/install/install.sh && chmod +x install.sh
		./install.sh --user=st2admin --password=Ch@ngeMe --license=<License-Key>
(The username: “st2admin” and password: “Ch@ngeMe” is the default and can be changed)

### Install MySQL Server:
		sudo apt-get install mysql-server
		sudo mysql_secure_installation
(The username and password will be needed later on.)

### Create the database and tables in MySQL
		mysql -u <username> -p
		CREATE database users;
		USE users;
		CREATE table failures (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, timestamp VARCHAR(20), switch_name VARCHAR(30), mac VARCHAR(20), ip VARCHAR(20), device VARCHAR(30), port VARCHAR (10));
		CREATE table authorized (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, timestamp VARCHAR(20), switch_name VARCHAR(30), mac VARCHAR(20), base_mac VARCHAR(20), ip VARCHAR(20), device VARCHAR(30), port varchar (10));

Add your authorized macs and device names to the authorized table. Writing a script to do this would be the most efficient way to do this. But the command below demonstrates how this can be done in MySQL:
		
		INSERT INTO authorized (mac, device) values('0000.0000.0000', 'Ruckus_AP_BLD1');

### Install rsyslog
		sudo apt-get install rsyslog
Configure rsyslog to store logs in: "/var/log/syslog" and the permissions need to allow reading.

## Create a sensorlog file and configure permissions
		touch /var/log/sensorlog
		chmod 666 /var/log/sensorlog

## Setup BWC Datastore
Ensure that you've set up BWC for encrypted datastore. See https://docs.stackstorm.com/datastore.html

And then add the following items (replacing it with your username and password)

		st2 key set campus_ztp.username 'ICX_Switch_SSH_Username'
		st2 key set campus_ztp.password 'ICX_Switch_SSH_Passworsd' --encrypt
		st2 key set campus_ztp.enable_username 'ICX_Switch_Enable_Username'
		st2 key set campus_ztp.enable_password 'ICX_Switch_Enable_Password' –encrypt
		st2 key set campus_ztp.db_user 'MySQL_Username' --encrypt
		st2 key set campus_ztp.db_pass 'MySQL_Password' --encrypt
		st2 key set campus_ztp.db_name 'users’ --encrypt
		st2 key set campus_ztp.db_addr '127.0.0.1' --encrypt
		st2 key set campus_ztp.ruckus_controller_username 'Ruckus_Controller_Username'
		st2 key set campus_ztp.ruckus_controller_password 'Ruckus_Controller_Password' --encrypt
		st2 key set campus_ztp.ruckus_controller_enable_username 'Ruckus_Controller_Enable_Username'
		st2 key set campus_ztp.ruckus_controller_enable_password 'Ruckus_Controller_Enable_Password' --encrypt


## Pack Installation
### Via git

		st2 pack install https://github.com/pjimmybrcd/campus_ztp_nps.git
		st2ctl reload

### Manual Install
You can also move the entire pack to the /opt/stackstorm/packs/ directory then install by issuing the following commands.

1. Rename the folder to campus_ztp
2. Move the campus_ztp folder to /opt/stackstorm/packs/
3. Load the pack

		st2ctl reload
		st2 run packs.setup_virtualenv packs=campus_ztp

To view the pack online navigate to https://github.com/pjimmybrcd/campus_ztp_nps

## Pack Removal
To remove an installed pack from BWC do the following:

		st2 pack remove campus_ztp

# Solution Troubleshooting
The following information may be helpful to troubleshoot any issues that arise.

## ICX Template Configuration
The template that is sent to the ICX will need to be updated depending on the configuration changes that are needed. The changes that are currently made by the template include updating the vlan, mac auth, and port name.
1. Modify the template:
		
		/opt/stacktorm.packs/campus_ztp/templates/icx_vlan_update

2. Test the template in the terminal:

		st2 run campus_ztp.send_cli_template template='icx_vlan_update' device='<ICX_IP_Address>' variables='{"commit":"true","port":"1/1/1","ap_name":"Ruckus_AP_BLD1"}'

3. Reload the pack:

		st2ctl reload

# Campus ZTP
Edit the config.yaml for your environment

* `templates` - directory where templates are stored
* `excel` - location of excel spreadsheet of configuration data
* `config_backup_dir` - location of switches backup files
* `tmp_dir` - location where configuration file will be temporary stored before SCP

## Open BWC GUI
Open the internet browser and navigate to: http://bwc_ip_address

## List Sensors
		st2 sensor list

## Debugging campus_ztp sensor
		sudo /opt/stackstorm/st2/bin/st2sensorcontainer --config-file=/etc/st2/st2.conf --sensor-ref=campus_ztp.LoggingWatchSensor

## Tailing the Syslog messages
		tail –f /var/log/syslog

## Tailing the Sensor messages
		tail –f /var/log/sensorlog

## Tailing the Sensor Container messages
		tail –f /var/log/st2/st2sensorcontainer.log

## List Rows of Authorized table in Database
		mysql -u <username> -p
		USE users;
		select * from authorized;
		exit

## List Rows of Failures table in Database
		mysql -u <username> -p
		USE users;
		select * from failures;
		exit

## Test sending a Template to ICX Switch
		st2 run campus_ztp.send_cli_template template='icx_vlan_update' device='<ICX_IP_Address>' variables='{"commit":"true","port":"1/1/1","ap_name":"Ruckus_AP_BLD1"}'


The best way to troubleshoot any issues is to first open the BWC GUI and look at the logs for any action with a red status. Is there are no actions being called, it is most likely an issue at the sensor level. Tail the log and debug the campus_ztp sensor side-by-side by running the commands above in separate terminals. The sensor should display messages stating “should not allow” or “should allow” if a syslog message is matched. If a “should not allow” message is displayed when an authorized device fails MAC Auth, then verify that the MAC is in the Authorized table. 

To view the unauthorized devices that were connected to the switch, list the rows of the failures table.

If the configuration change fails, use the command to test sending a template to ensure that the template is written correctly.

## Additional Notes:
The sensor being used, logging_sensor, tails a log file on the BWC machine.
In the config.yaml file the LoggingWatchSensor and SyslogWatchSensor are set to look at the "/var/log/syslog" log file. You will need to rename this file if you are logging to a different file.

## License
Copyright 2016 Brocade Communications Systems, Inc.
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
