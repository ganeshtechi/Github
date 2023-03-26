Terraform workspace help us to create infrastructure with single terraform files

#To create new workspace 

terraform create workspace new dev

#To list all workspaces

terraform workspace list

#To see the active workspace

terraform workspace show 

#To switch between workspaces

terraform workspace select dev_workspace

provider "aws" {
region = "us-east-1"
access key = ""
secret key = ""
}

locals {
  instance name = "${terraform.workspace}-instance"
  #terraform workspace is the name variable that I'm referring
}
resource "aws instance" "ec2 example" {
  ami = "ami-0767046d1677be5a0"
  instance type = "t2_nano"
  tags = { 
    Name = local.instance_name
  }
}

