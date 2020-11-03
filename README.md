# PBO3 Inventory-gen

Ansible dynamic inventory plugin for PBO3.
Generates an ansible inventory from the pbo3 server database.

## Setup
### Install modules
```
pip install -r requirements.txt
```
### Set variables
```
export ANSIBLE_INVENTORY_ENABLED="pbo3"
export ANSIBLE_INVENTORY_PLUGINS="path/to/the/inventory/directory"
```
## Usage
Add your variables in inventory.yaml file.
"password" is optional and the script will prompt for a password if the line is commented.
When you start your playbook just add the inventory
```
ansible-playbook playbook.yaml -i inventory.yaml
```
