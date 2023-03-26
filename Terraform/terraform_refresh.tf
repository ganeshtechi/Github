#The command is used to update state file to match with running resources
#If you delete any resource manually and run the refresh command then the statefile will be updated.
#Terraform refresh will not modify remote objects, but will modify the terraform state
#Command: terraform refresh
#Command in latest version: terraform apply -refresh-only -auto-approve


provider "aws" {
	region = "us-east-1"
}

terraform {
  backend "s3" {
    bucket = "terraform-prod-statefile"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}

resource "aws_vpc" "default" {
  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true

  
}

resource "aws_subnet" "public-subnet" {
  vpc_id = "${aws_vpc.default.id}"
  cidr_block = "10.0.1.0/24"
  availability_zone = "us-east-1a"

}

resource "aws_security_group" "sgweb" {
  name = "vpc_test_web"
  description = "Allow incoming HTTP connections & SSH access"

  ingress {
    from_port = 80
    to_port = 80
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 443
    to_port = 443
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = -1
    to_port = -1
    protocol = "icmp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks =  ["0.0.0.0/0"]
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }

  vpc_id="${aws_vpc.default.id}"

}

resource "aws_instance" "web" {
	ami = "ami-032930428bf1abbff"
	instance_type = "t2.micro"
	subnet_id = "${aws_subnet.public-subnet.id}"
	vpc_security_group_ids = ["${aws_security_group.sgweb.id}"]
}


resource "aws_s3_bucket" "my_bucket" {
  bucket = "testing_terraform_bucket"
  acl    = "private"

  tags = {
    Name        = "dev bucket"
    Environment = "Dev"
  }
}

#Here if we delete S3 Bucket manually in the console, refresh will update state.
