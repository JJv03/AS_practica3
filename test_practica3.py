#!/usr/bin/env python3

# WARNING!!!
# this script should be run in a chrooted environment

import os
import pexpect
import random
import re
from subprocess import check_call
import string
import sys
from tempfile import mkstemp
import unittest

class TestPractica3(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """ Find script directory and store its name in a variable """
        cls.my_dir=os.path.dirname(os.path.realpath(__file__))
        cls.script_name=os.path.realpath('{}/../practica_3/practica_3.sh'.format(cls.my_dir))

    # clean before every test, just in case something goes wrong
    def setUp(self):
        check_call(["/bin/bash", "{}/../utils/remove_possible_users.sh".format(self.my_dir)])

    def tearDown(self):
        try:
            self.child.terminate(force=True)
        except:
            None

    def test_shebang(self):
        with open(self.script_name) as f:
            first_line = f.readline().rstrip('\r\n')

            pattern=re.compile('#!/usr/bin/env\s+bash')
            # two options: #!/bin/bash or #!/usr/bin/env bash
            self.assertTrue((first_line == '#!/bin/bash') or
                    (pattern.match(first_line) != None))

    def test_required_commands(self):
        """ This test checks for required commands and options for useradd
        """

        def ensure_useradd_options(required_options, word_list):
            """ Given a list of words, this functions removes useradd options
                if they exists:
                -U
                -k /etc/skel
                -K UID_MIN=1815
                -c
             """

            idx=words_in_line.index('useradd')
            lenght=len(words_in_line)

            if '-U' in words_in_line:
                required_options.remove('-U')
            # ToDo double-check that the name is correct
            if '-c' in words_in_line:
                required_options.remove('-c')

            if '-k' in words_in_line[idx:-1]:
                idx_k=words_in_line.index('-k')
                if lenght > idx_k + 1 :
                    required_options.discard('-k {}'.format(words_in_line[idx_k+1]))

            # useradd can have multiple -K options
            for idx_k in [ i for i, word in enumerate(words_in_line[idx:]) if word == '-K' ]:
                if idx_k+1 < lenght:
                    required_options.discard('-K {}'.format(words_in_line[idx_k+1]))

            if '-K' in words_in_line[idx:-1]:
                idx_k=words_in_line.index('-K')

            return required_options

        required_commands=set(['useradd', 'userdel', 'usermod', 'chpasswd', 'tar'])
        required_useradd_options=set(['-U', '-k /etc/skel', '-K UID_MIN=1815', '-c'])

        with open(self.script_name) as f:
            # flag for checking that at least one invocation to useradd includes all required options
            for full_line in f:
                # remove spaces at beginning of line and end of lines
                l = full_line.lstrip().rstrip('\n')

                # skip empty and commented lines
                if not l or l[0] == '#':
                    continue
                words_in_line=l.split()

                # remove commented parts in valid lines
                if '#' in words_in_line:
                    idx=words_in_line.index('#')
                    words_in_line=words_in_line[:idx]

                # verify the script does not include sudo
                self.assertFalse('sudo' in words_in_line,
                        msg='Line {} contains the sudo command'.format(l))

                # only check if there are pending commands
                if required_commands:
                    for word in words_in_line:
                        required_commands.discard(word)

                if required_useradd_options and 'useradd' in words_in_line:
                    ensure_useradd_options(required_useradd_options,
                            words_in_line)

            self.assertFalse(required_commands,
                    msg='The script does not contain all required commands.'
                    ' Missing commands are: {}'.format(
                        ", ".join(required_commands)))

            self.assertFalse(required_useradd_options,
                    msg='The script does not contain all required useradd options.'
                    ' Missing options are: {}'.format(
                        ", ".join(required_useradd_options)))


    def test_number_arguments(self):
        self.child = pexpect.spawn('sudo /bin/bash "{}" -a "{}/correct_user_list.txt" extra_arg'.format(self.script_name, self.my_dir), encoding='utf8')
        try:
            self.child.expect_exact('Numero incorrecto de parametros\r\n')
        except:
            self.assertTrue(False)
        self.assertTrue(True)

    def test_sudo(self):
        self.child = pexpect.spawn('/bin/bash "{}" -a "{}/correct_user_list.txt"'.format(self.script_name, self.my_dir), encoding='utf8')
        try:
            self.child.expect_exact('Este script necesita privilegios de administracion')
        except:
            self.assertTrue(False)
        self.assertTrue(True)

    def test_invalid_argument(self):
        self.child = pexpect.spawn('sudo -- /bin/bash "{}" -I "{}/correct_user_list.txt'.format(self.script_name, self.my_dir), encoding='utf8')
        try:
            self.child.expect_exact('Opcion invalida')
        except:
            self.assertTrue(False)

        try:
            self.assertFalse(self.child.expect(pexpect.EOF))
        except:
            self.assertTrue(False)

    def test_create_extra_backup(self):
        # risky test, it deletes a directory
        backup_dir='/extra/backup'

        if os.path.isdir(backup_dir):
            check_call(["sudo", "rm", "-rf", '{}'.format(backup_dir)])

        self.child = pexpect.spawn('sudo', ['--', '/bin/bash', '{}'.format(self.script_name), '-s', '/dev/null'], encoding='utf8')
        try:
            self.child.expect(pexpect.EOF)
        except:
            self.assertTrue(False)

        self.child.close()
        self.assertEqual(self.child.exitstatus, 0)
        self.assertTrue(os.path.isdir(backup_dir))

    def test_login_users(self):
        """ Try to su into the newly created users
        """

        with open(os.devnull, 'w') as FNULL:
            check_call(["sudo", "--", "/bin/bash", "{}".format(self.script_name), "-a", "{}/correct_user_list.txt".format(self.my_dir)],
                    stdout=FNULL, stderr=FNULL)

        with open('{}/correct_user_list.txt'.format(self.my_dir), 'r') as f:
            for line in f:
                user, pwd, name = [ w.rstrip(' \n').lstrip(' ') for w in line.split(',') ]

                self.child = pexpect.spawn('su {}'.format(user), encoding='utf8')
                try:
                    self.child.expect_exact(['Password: ', 'Contraseña: '])
                except:
                    self.assertTrue(False, msg='Unable to run su')
                self.child.sendline(pwd)
                try:
                    self.child.expect('\$')
                except:
                    self.assertTrue(False, msg='Unable to login with su')
                self.child.sendline('exit')

                try:
                    self.assertFalse(self.child.expect(pexpect.EOF))
                except:
                    self.assertTrue(False, msg='Invalid exit')

                self.child.close()

    def test_correct_user_list(self):
        self.child = pexpect.spawn('sudo -- /bin/bash "{}" -a "{}/correct_user_list.txt"'.format(self.script_name, self.my_dir), encoding='utf8')

        with open('{}/correct_user_list.txt'.format(self.my_dir), 'r') as f:
            for line in f:
                user, pwd, name = [ w.rstrip(' \n').lstrip(' ') for w in line.split(',') ]
                try:
                    expected_string="{} ha sido creado".format(name)
                    self.child.expect_exact(expected_string)
                except:
                    self.assertTrue(False)

        try:
            self.assertFalse(self.child.expect(pexpect.EOF))
        except:
            self.assertTrue(False)

    def test_root_user(self):
        self.child = pexpect.spawn('sudo -- /bin/bash "{}" -a "{}/incorrect_user_list_existing_root.txt"'.format(self.script_name, self.my_dir), encoding='utf8')

        try:
            self.child.expect_exact('El usuario root ya existe')
        except:
            self.assertTrue(False)

        try:
            self.assertFalse(self.child.expect(pexpect.EOF))
        except:
            self.assertTrue(False)

    def get_new_user(self):
        """ This helper function returns a valid name for a new user
        """
        users=set()
        with open('/etc/passwd', 'r') as f:
            for line in f:
                users.add(line.split(':')[0])

        random_user_name=''.join(random.choice(string.ascii_letters+string.digits) for _ in range(8))
        while random_user_name in users:
            random_user_name=''.join(random.choice(string.ascii_letters+string.digits) for _ in range(8))
        return random_user_name

    def create_fake_user_file(self, user_name, fake_home=False):
        """ this function returns the name of a temporary file with a new user named user_name.
            The file has been closed and it is the caller responsability to remove the generated file.
        """

        tmp_handle, tmp_name = mkstemp()

        command_list = [ "sudo", "useradd", "-m" ]

        if fake_home:
            command_list += ["-d", "/tmp/{}".format(user_name)]

        command_list += ["{}".format(user_name)]
        check_call(command_list)

        os.write(tmp_handle, '{}, {}, {}\n'.format(user_name, 'pwd' + user_name, 'name' + user_name).encode())
        os.close(tmp_handle)

        return tmp_name

    def test_remove_user_uncommon_home(self):
        """ Remove a user whom $HOME is not in /home
        """
        random_user_name=self.get_new_user()
        tmp_name = self.create_fake_user_file(random_user_name, fake_home=True)

        # run the script
        self.child = pexpect.spawn('sudo', ['--', '/bin/bash', '{}'.format(self.script_name), '-s', tmp_name], encoding='utf8')

        try:
            self.child.expect(pexpect.EOF)
        except:
            os.unlink(tmp_name)
            self.assertTrue(False)

        # verify the user is not in the system and the backup has been created
        users=set()
        with open('/etc/passwd', 'r') as f:
            for line in f:
                users.add(line.split(':')[0])

        self.assertFalse(random_user_name in users)
        self.assertTrue(os.path.isfile('/extra/backup/' + random_user_name + ".tar"))
        os.unlink(tmp_name)

    def test_remove_existing_user(self):

        random_user_name=self.get_new_user()
        tmp_name = self.create_fake_user_file(random_user_name)

        # run the script
        self.child = pexpect.spawn('sudo', ['--', '/bin/bash', '{}'.format(self.script_name), '-s', tmp_name], encoding='utf8')
        self.child.logfile = sys.stdout
        try:
            self.assertFalse(self.child.expect(pexpect.EOF))
        except:
            os.unlink(tmp_name)
            self.assertTrue(False)

        # verify the user is not in the system and the backup has been created
        users=set()
        with open('/etc/passwd', 'r') as f:
            for line in f:
                users.add(line.split(':')[0])

        self.assertFalse(random_user_name in users)
        self.assertTrue(os.path.isfile('/extra/backup/' + random_user_name + ".tar"))
        os.unlink(tmp_name)

    def test_existing_user(self):

        random_user_name=self.get_new_user()
        tmp_name = self.create_fake_user_file(random_user_name)

        null_file=open(os.devnull, 'w')

        self.child = pexpect.spawn('sudo', ['--', '/bin/bash', '{}'.format(self.script_name), '-a', tmp_name], encoding='utf8')

        try:
            expected_string='El usuario {} ya existe'.format(random_user_name)
            self.child.expect_exact(expected_string)
        except:
            # ensure the newly created user is deleted
            check_call(["sudo", "userdel", "-r", "-f", "{}".format(random_user_name)],
                    stdout=null_file, stderr=null_file)
            self.assertTrue(False, msg='Expected: {}\nFound: {}'.format(expected_string, self.child.before))
            os.unlink(tmp_name)
            null_file.close()

        try:
            self.assertFalse(self.child.expect(pexpect.EOF))
        except:
            self.assertTrue(False)

        check_call(["sudo", "userdel", "-r", "-f", "{}".format(random_user_name)],
                    stdout=null_file, stderr=null_file)
        os.unlink(tmp_name)
        null_file.close()

if __name__ == "__main__":
    unittest.main()
