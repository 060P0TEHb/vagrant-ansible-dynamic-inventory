#!/usr/bin/env python
# Adapted from Mark Mandel's implementation
# https://github.com/ansible/ansible/blob/devel/plugins/inventory/vagrant.py
import argparse
import json
import paramiko
import subprocess
import sys
 
 
def parse_args():
    parser = argparse.ArgumentParser(description="Vagrant inventory script")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true')
    group.add_argument('--host')
    return parser.parse_args()
 

def list_running_hosts():
    result = {}
    hosts = []
    default_group = "default"
    try:
        cmd = "vagrant status --machine-readable"
        status = subprocess.check_output(cmd.split(), universal_newlines=True).rstrip()
        for line in status.split('\n'):
            (_, host, key, value) = line.split(',',3)
            if key == 'state' and value == 'running':
                hosts.append(host)

        for host in hosts:
            # get vm's id
            cmd = "vboxmanage list runningvms | grep {}".format(host)
            id_vm = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            vm = str(id_vm.communicate())
            vm = vm[vm.find('{')+1:vm.find('}')]
            # get description and parse to groups
            cmd = "vboxmanage showvminfo {} --machinereadable | grep description".format(vm)
            description = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            groups = (description.communicate())[0]
            if len(groups) != 0:
                groups = groups.split('"')[1].split(':')[1].strip().split(',')
            else:
                groups = [default_group]
            for g in groups:
                g = g.strip()
                if g in result:
                  result[g].append(host)
                else:
                  result[g] = [host]
    except subprocess.CalledProcessError:
        # get vm's id
        cmd = "vboxmanage list runningvms"
        id_vm = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        
        for line in id_vm.communicate()[0].split('\n')[:-1]:
            # get description and parse to groups
            cmd = "vboxmanage showvminfo {} --machinereadable | grep description".format(line[line.find('{')+1:line.find('}')])
            description = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            groups = (description.communicate())[0]
            if len(groups) != 0:
                groups = groups.split('"')[1].split(':')[1].strip().split(',')
            else:
                groups = [default_group]
            for g in groups:
                g = g.strip()
                if g in result:
                  result[g].append(line[line.find('"')+1:line.find('"',1)])
                else:
                  result[g] = [line[line.find('"')+1:line.find('"',1)]]
    return result
 
def get_host_details(host):
    try:
        cmd = "vagrant ssh-config {}".format(host)
        p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
        config = paramiko.SSHConfig()
        config.parse(p.stdout)
        c = config.lookup(host)
        return {'ansible_ssh_host': c['hostname'],
                'ansible_ssh_port': c['port'],
                'ansible_ssh_user': c['user'],
                'ansible_ssh_private_key_file': c['identityfile'][0],
                'ansible_python_interpreter': '/usr/bin/python3'}
    except:
        c = {}
        cmd = "VBoxManage guestproperty enumerate " + host + " | grep IP | \
               grep -o -w -P -e '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
        ip = (p.communicate())[0]
        if '10.0.2.15' in ip:
            cmd = "VBoxManage showvminfo {} | grep ssh".format(host)
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
            ip = (p.communicate())[0]
            ip = ip.split(':')[1].strip()
            for i in ip.split(','):
                k,v = i.strip().split('=')
                c[k.strip()] = v.strip()
            return {'ansible_ssh_host': c['host ip'],
                    'ansible_ssh_port': c['host port'],
                    'ansible_python_interpreter': '/usr/bin/python3'}
        else:
            return {'ansible_ssh_host': ip[:-1],
                    'ansible_python_interpreter': '/usr/bin/python3'}
 
 
def main():
    args = parse_args()
    if args.list:
        hosts = list_running_hosts()
        json.dump(hosts, sys.stdout)
    else:
        details = get_host_details(args.host)
        json.dump(details, sys.stdout)
 
if __name__ == '__main__':
    main()
