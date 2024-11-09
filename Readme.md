# AWS + GCP + Azure template for Pulumi

## How to use template

```
import requests

github_url = "https://raw.githubusercontent.com/PouyaData/pulumi-AWS-GCP-Azure-templates/refs/heads/master/aws_component.py"
response = requests.get(github_url)
print(response.status_code)
if response.status_code == 200:
    print("AWS component loaded")
exec(response.text, globals())
```