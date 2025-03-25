from base.cloud_service import CloudServiceComponent
# import pulumi
# import pulumi_azure as azure
# import pulumi_azure_native as azure_native
# import pulumi_command as command

import pulumi
from pulumi_azure_native import resources, network, compute
from pulumi_random import random_string
import pulumi_tls as tls
import base64

class AzureComponent(CloudServiceComponent):
    def __init__(self, config):
        # Get config values
        self.config = config        


    def create_key_vault(self):
        # Logic for accessing secrets from Azure Key Vault
        # key_vault_name = self.config.get("key_vault_name")
        # subscription_id = self.config.get("subscription_id")
        # print(subscription_id)
        # resource_group_name = self.config.get("resource_group_name")

        # key_vault_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.KeyVault/vaults/{key_vault_name}"

        # # Get secrets from Key Vault
        # # admin_username = azure.keyvault.get_secret(name="adminUsername", key_vault_id=key_vault_id).value
        # # admin_password = azure.keyvault.get_secret(name="adminPassword", key_vault_id=key_vault_id).value

        # self.admin_username = "admin"
        # self.admin_password = "Super!@#$$#@!1234"


    def create_network(self):
        # Logic for creating a Virtual         
        # appname = pulumi.get_project()
        # location = self.config.get("location")
        # resource_group_name = self.config.get("resource_group_name")

        # virtual_network = azure_native.network.VirtualNetwork("virtualNetwork",
        #     address_space={
        #         "addressPrefixes": ["10.0.0.0/16"],
        #     },
        #     location=location,
        #     resource_group_name=resource_group_name,
        #     virtual_network_name=f"{appname}-azure-vn")

        # subnet = azure_native.network.Subnet("subnet",
        #     address_prefix="10.0.0.0/16",
        #     resource_group_name=resource_group_name,
        #     subnet_name=f"{appname}-azure-sn",
        #     virtual_network_name=virtual_network.name)

        # self.subnet_id = subnet.id

        # # Logic for creating a Public IP Address
        # location = self.config.get("location")
        # resource_group_name = self.config.get("resource_group_name")

        # public_ip = azure_native.network.PublicIPAddress(f"publicIP-azure",
        #     resource_group_name=resource_group_name,
        #     location=location,
        #     public_ip_allocation_method="Dynamic")

        # self.public_ip_id = public_ip.id

    
    def create_instance(self):
        # Import the program's configuration settings
        config = pulumi.Config()
        vm_name = config.get("vmName", "my-server")
        vm_size = config.get("vmSize", "Standard_A1_v2")
        os_image = config.get("osImage", "Debian:debian-11:11:latest")
        admin_username = config.get("adminUsername", "pulumiuser")
        service_port = config.get("servicePort", "80")
        
        os_image_publisher, os_image_offer, os_image_sku, os_image_version = os_image.split(":")
        
        # Create an SSH key
        ssh_key = tls.PrivateKey(
            "ssh-key",
            algorithm="RSA",
            rsa_bits=4096,
        )
        
        # Create a resource group
        resource_group = resources.ResourceGroup("resource-group")
        
        # Create a virtual network
        virtual_network = network.VirtualNetwork(
            "network",
            resource_group_name=resource_group.name,
            address_space={
                "address_prefixes": [
                    "10.0.0.0/16",
                ],
            },
            subnets=[
                {
                    "name": f"{vm_name}-subnet",
                    "address_prefix": "10.0.1.0/24",
                },
            ],
        )
        # Use a random string to give the VM a unique DNS name
        domain_name_label = random_string.RandomString(
            "domain-label",
            length=8,
            upper=False,
            special=False,
        ).result.apply(lambda result: f"{vm_name}-{result}")
        
        # Create a public IP address for the VM
        public_ip = network.PublicIPAddress(
            "public-ip",
            resource_group_name=resource_group.name,
            public_ip_allocation_method=network.IpAllocationMethod.DYNAMIC,
            dns_settings={
                "domain_name_label": domain_name_label,
            },
        )
        
        # Create a security group allowing inbound access over ports 80 (for HTTP) and 22 (for SSH)
        security_group = network.NetworkSecurityGroup(
            "security-group",
            resource_group_name=resource_group.name,
            security_rules=[
                {
                    "name": f"{vm_name}-securityrule",
                    "priority": 1000,
                    "direction": network.AccessRuleDirection.INBOUND,
                    "access": "Allow",
                    "protocol": "Tcp",
                    "source_port_range": "*",
                    "source_address_prefix": "*",
                    "destination_address_prefix": "*",
                    "destination_port_ranges": [
                        service_port,
                        "22",
                    ],
                },
            ],
        )
        
        # Create a network interface with the virtual network, IP address, and security group
        network_interface = network.NetworkInterface(
            "network-interface",
            resource_group_name=resource_group.name,
            network_security_group={
                "id": security_group.id,
            },
            ip_configurations=[
                {
                    "name": f"{vm_name}-ipconfiguration",
                    "private_ip_allocation_method": network.IpAllocationMethod.DYNAMIC,
                    "subnet": {
                        "id": virtual_network.subnets.apply(lambda subnets: subnets[0].id),
                    },
                    "public_ip_address": {
                        "id": public_ip.id,
                    },
                },
            ],
        )
        
        # Define a script to be run when the VM starts up
        init_script = f"""#!/bin/bash
            echo '<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="utf-8">
                <title>Hello, world!</title>
            </head>
            <body>
                <h1>Hello, world! 👋</h1>
                <p>Deployed with 💜 by <a href="https://pulumi.com/">Pulumi</a>.</p>
            </body>
            </html>' > index.html
            sudo python3 -m http.server {service_port} &
            """
        
        # Create the virtual machine
        vm = compute.VirtualMachine(
            "vm",
            resource_group_name=resource_group.name,
            network_profile={
                "network_interfaces": [
                    {
                        "id": network_interface.id,
                        "primary": True,
                    }
                ]
            },
            hardware_profile={
                "vm_size": vm_size,
            },
            os_profile={
                "computer_name": vm_name,
                "admin_username": admin_username,
                "custom_data": base64.b64encode(bytes(init_script, "utf-8")).decode("utf-8"),
                "linux_configuration": {
                    "disable_password_authentication": True,
                    "ssh": {
                        "public_keys": [
                            {
                                "key_data": ssh_key.public_key_openssh,
                                "path": f"/home/{admin_username}/.ssh/authorized_keys",
                            },
                        ],
                    },
                },
            },
            storage_profile={
                "os_disk": {
                    "name": f"{vm_name}-osdisk",
                    "create_option": compute.DiskCreateOption.FROM_IMAGE,
                },
                "image_reference": {
                    "publisher": os_image_publisher,
                    "offer": os_image_offer,
                    "sku": os_image_sku,
                    "version": os_image_version,
                },
            },
        )
        
        # Once the machine is created, fetch its IP address and DNS hostname
        vm_address = vm.id.apply(
            lambda id: network.get_public_ip_address_output(
                resource_group_name=resource_group.name,
                public_ip_address_name=public_ip.name,
            )
        )
        
        # Export the VM's hostname, public IP address, HTTP URL, and SSH private key
        pulumi.export("ip", vm_address.ip_address)
        pulumi.export("hostname", vm_address.dns_settings.apply(lambda settings: settings.fqdn))
        pulumi.export(
            "url",
            vm_address.dns_settings.apply(
                lambda settings: f"http://{settings.fqdn}:{service_port}"
            ),
        )
        pulumi.export(
            "privatekey",
            ssh_key.private_key_openssh,
        )
