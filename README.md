# PBO3 Inventory-gen

Ansible dynamic inventory plugin for PBO3

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
When you start your playbook just add the inventory
```
ansible-playbook playbook.yaml -i inventory.yaml
```
