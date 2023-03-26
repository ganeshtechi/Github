#This is the parent tf file

provider "aws" {
  region = "us-east-1"
  access key = ""
  secret key = ""
}

module "dev-webserver-module" {
  #Module name is user defined, we can keep any name
  source = ".//webserver-module"
}

module "dev-appserver-module" {
  #Module name is user defined, we can keep any name
  source = ".//appserver-module"
}
