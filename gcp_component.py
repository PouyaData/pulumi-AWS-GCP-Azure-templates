from base.cloud_service import CloudServiceComponent
import pulumi
import pulumi_gcp as gcp

class GCPComponent(CloudServiceComponent):
    def __init__(self, config):
        # Get config values
        self.config = config
        

    # def create_key_vault(self):        
    #     ssh_key_path = os.path.expanduser("~/.ssh/my-gcp-key.pub")
        
    #     if not os.path.exists(ssh_key_path):
    #         raise FileNotFoundError(f"SSH public key not found: {ssh_key_path}")
            
    #     # Read the public key from the file
    #     with open(ssh_key_path, 'r') as pub_key_file:
    #         public_key = pub_key_file.read().strip()
    #     self.public_key = public_key


    # def create_network(self):
    #     # Logic for creating a Firewall rule to allow HTTP and SSH traffic
    #     firewall_rule = gcp.compute.Firewall("web-firewall",
    #         network="default",
    #         allows=[
    #             gcp.compute.FirewallAllowArgs(
    #                 protocol="tcp",
    #                 ports=["80"],
    #             ),
    #             gcp.compute.FirewallAllowArgs(
    #                 protocol="tcp",
    #                 ports=["22"],
    #             ),
    #         ],
    #         source_ranges=["0.0.0.0/0"],
    #         target_tags=["http-server", "ssh-server"]
    #     )        


    # def create_instance(self):
    #     # Logic for creating a VM instance
    #     instance = gcp.compute.Instance("my-instance",
    #         machine_type="e2-medium",  # Example machine type
    #         zone="us-central1-c",
    #         boot_disk=gcp.compute.InstanceBootDiskArgs(
    #             initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
    #                 image="ubuntu-minimal-2004-focal-v20240812",  # Example image
    #             ),
    #         ),
    #         network_interfaces=[gcp.compute.InstanceNetworkInterfaceArgs(
    #             network="default",
    #             access_configs=[gcp.compute.InstanceNetworkInterfaceAccessConfigArgs()],  # Allocate a new ephemeral public IP address
    #         )],
    #         metadata={
    #             "ssh-keys": f"ubuntu:{self.public_key}"  # Use the SSH public key
    #         },
    #         tags=["http-server", "ssh-server"],  # Tags to match firewall rules
    #         metadata_startup_script="""#!/bin/bash
    #         # Update and install Nginx
    #         sudo apt-get update -y
    #         sudo apt-get install -y nginx

    #         # Create Nginx configuration file
    #         sudo bash -c 'cat > /etc/nginx/sites-available/default' << 'EOF'
    #         server {
    #             listen 80;
    #             server_name localhost;
    #             root /var/www/html;
    #             index index.html index.htm index.nginx-debian.html;
    #             location / {
    #                 try_files \\$uri \\$uri/ =404;
    #             }
    #         }
    #         server {
    #             listen 80;
    #             location / {
    #                 proxy_pass http://localhost;
    #                 proxy_set_header Host \\$host;
    #                 proxy_set_header X-Real-IP \\$remote_addr;
    #                 proxy_set_header X-Forwarded-For \\$proxy_add_x_forwarded_for;
    #                 proxy_set_header X-Forwarded-Proto \\$scheme;
    #             }
    #         }
    #         EOF

    #         # Restart Nginx to apply changes
    #         sudo systemctl restart nginx
    #         """,
    #     )

    #     self.instance_id = instance.id
    #     self.public_ip = instance.network_interfaces[0].access_configs[0].nat_ip
    #     self.private_ip = instance.network_interfaces[0].network_ip
    def create_instance(self):
        config = pulumi.Config()
        machine_type = config.get("machineType", "f1-micro")
        os_image = config.get("osImage", "debian-11")
        instance_tag = config.get("instanceTag", "webserver")
        service_port = config.get("servicePort", "80")
        
        # Create a new network for the virtual machine.
        network = gcp.compute.Network(
            "network",
            auto_create_subnetworks=False,
        )
        
        # Create a subnet on the network.
        subnet = gcp.compute.Subnetwork(
            "subnet",
            ip_cidr_range="10.0.1.0/24",
            region="us-central1",
            network=network.id,
        )
        
        # Create a firewall allowing inbound access over ports 80 (for HTTP) and 22 (for SSH).
        firewall = gcp.compute.Firewall(
            "firewall",
            network=network.self_link,
            allows=[
                {
                    "protocol": "tcp",
                    "ports": [
                        "22",
                        service_port,
                    ],
                },
            ],
            direction="INGRESS",
            source_ranges=[
                "0.0.0.0/0",
            ],
            target_tags=[
                instance_tag,
            ],
        )
        
        # Define a script to be run when the VM starts up.
        metadata_startup_script = f"""#!/bin/bash
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
        
        # Create the virtual machine.
        instance = gcp.compute.Instance(
            "instance",
            machine_type=machine_type,
            zone="us-central1-a",
            boot_disk={
                "initialize_params": {
                    "image": os_image,
                },
            },
            network_interfaces=[
                {
                    "network": network.id,
                    "subnetwork": subnet.id,
                    "access_configs": [],
                },
            ],
            service_account={
                "scopes": [
                    "https://www.googleapis.com/auth/cloud-platform",
                ],
            },
            metadata={
                "enable-oslogin": "TRUE",
            },
            allow_stopping_for_update=True,
            metadata_startup_script=metadata_startup_script,
            tags=[
                instance_tag,
            ],
            opts=pulumi.ResourceOptions(depends_on=firewall),
        )
        
        instance_ip = instance.network_interfaces.apply(
            lambda interfaces: interfaces[0].access_configs
            and interfaces[0].access_configs[0].nat_ip
        )
        
        # Export the instance's name, public IP address, and HTTP URL.
        pulumi.export("name", instance.name)
        pulumi.export("ip", instance_ip)
        pulumi.export("url", instance_ip.apply(lambda ip: f"http://{ip}:{service_port}"))
