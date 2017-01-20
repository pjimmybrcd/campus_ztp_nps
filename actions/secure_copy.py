"""
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
"""

from lib import actions, Secure_Copy, ztp_utils


class SecureCopyAction(actions.SessionAction):
    def __init__(self, config):
        super(SecureCopyAction, self).__init__(config)

    def run(self, hostname, source, destination, direction, username='', password=''):
        ztp_utils.replace_default_userpass(self, username, password,
                                           enable_username='', enable_password='')

        scp = Secure_Copy.Secure_Copy(hostname, self._username, self._password)

        # TODO: This should be done when keys are re-generated
        scp.erase_existing_ssh_key_for_host()

        if direction == 'to':
            success = scp.send_file(source, destination)
        if direction == 'from':
            success = scp.get_file(source, destination)
        if success:
            return (True, "File Copied!")
        else:
            return (False, "Failed")
