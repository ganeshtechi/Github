#If the resouce created outside of the terraform and wants to manage with terraform then we can use terraform import command

#In terraform main file, define a resource that matches in the remote resource

#Example, a VPC is created outside of terraform which we want to manage with manage with terraform 


provider "aws" {
	region = "us-east-1"
}

resource "aws_vpc" "outside_created_vpc" {
  cidr_block = "10.0.0.0/16"
  tags = {
    "Name" = "dev_vpc"
  }
}

#The CIDR block should match with the VPC that is created manually

#Command Usage

terraform import aws_vpc.outside_created_vpc vpc-a01106c2

#https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc
