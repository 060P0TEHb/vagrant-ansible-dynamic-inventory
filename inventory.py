#!/usr/bin/env python
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
    '''
    Func return list of hosts via vagrant cli or vboxmanage
    Groups got from vm's description. All vms witout groups set default_group 

    Example with vagrant cli:
      After split vagrant status --machine-readable we have next value
        nomad-master state running 
      vboxmanage list runningvms with grep
        "nomad-demo_nomad-master_1636135955454_7021" {f0d4fd09-6663-425f-8066-6f96e725d41c}
      vboxmanage showvminfo vm_id --machinereadable | grep description
        description="Ansible_groups: main_server, worker"
      result variable
        {'main_server': ['nomad-master'], 'worker': ['nomad-master']}

    Example with vboxmanage cli:
      vboxmanage list runningvms without grep
        "nomad-demo_nomad-master_1636135955454_7021" {f0d4fd09-6663-425f-8066-6f96e725d41c}
        ...
      For each vm are doing: vboxmanage showvminfo vm_id --machinereadable | grep description
        description="Ansible_groups: main_server, worker"
      result variable
        {'main_server': ['nomad-master'], 'worker': ['nomad-master']}
    '''
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
          cmd = "vboxmanage list runningvms | grep {}".format(host)
          id_vm = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
          vm = str(id_vm.communicate())
          vm = vm[vm.find('{')+1:vm.find('}')]
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
        cmd = "vboxmanage list runningvms"
        id_vm = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,\
                                 stderr=subprocess.STDOUT, universal_newlines=True)
        
        for line in id_vm.communicate()[0].split('\n')[:-1]:
            cmd = "vboxmanage showvminfo {} --machinereadable | \
                  grep description".format(line[line.find('{')+1:line.find('}')])
            description = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,\
                                           stderr=subprocess.STDOUT, universal_newlines=True)
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
    '''
    Func return configs for ansible for connection to vms via vagrant cli or vboxmanage
    Example with vagrant ssh-config
      Host nomad-master
        HostName 127.0.0.1
        User vagrant
        Port 2222
        ...
        IdentityFile /home/some_user/.vagrant.d/insecure_private_key
        ...

    If we catch KeyError
      'ansible_ssh_port': c['port'],
      KeyError: 'port'
    we go to vbox cli

    Example with vbox cli
      VBoxManage guestproperty enumerate host_name | grep IP | ...
        10.0.2.15 # vagrant_default_ip
        192.168.10.10
      If we found vagrant_default_ip:
        NIC 1 Rule(0):   name = ssh, protocol = tcp, host ip = 127.0.0.1, 
                         host port = 2222, guest ip = , guest port = 22 
      In other cases we only return founded IP
    '''
    vagrant_default_ip = '10.0.2.15'
    try:
      cmd = "vagrant ssh-config {}".format(host)
      p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,\
                           stderr=subprocess.DEVNULL, universal_newlines=True)
      config = paramiko.SSHConfig()
      config.parse(p.stdout)
      c = config.lookup(host)
      return {'ansible_ssh_host': c['hostname'],
              'ansible_ssh_port': c['port'],
              'ansible_ssh_user': c['user'],
              'ansible_ssh_private_key_file': c['identityfile'][0],
              'ansible_python_interpreter': '/usr/bin/python3'}
    except KeyError:
        c = {}
        cmd = "VBoxManage guestproperty enumerate " + host + " | grep IP | \
               grep -o -w -P -e '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
        ip = (p.communicate())[0]
        if vagrant_default_ip in ip:
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
