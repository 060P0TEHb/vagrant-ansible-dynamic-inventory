# vagrant-ansible-dynamic-inventory

### Example:
```
IMAGE_NAME = "some_image"

Vagrant.configure("2") do |config|
   ...
    config.vm.define "some_server" do |master|
        master.vm.box = IMAGE_NAME
        master.vm.provider "virtualbox" do |vm|
            vm.customize [ "modifyvm", :id, "--description", "Ansible_groups: main_server, worker" ]
            vm.memory = 1024
            vm.cpus = 1
        end
        master.vm.network "private_network", ip: "192.168.10.10"
        master.vm.hostname = "some_server"
        config.vm.provision "shell", inline: $script, privileged: false
    end
   ...
end
```
