#The state file contains all metadata information information of the resources 
#It will be created by terraform
#Storing terraform state file in S3 Bucket

terraform {
backend  "s3" {
  bucket = "terraform-state_bucket"
  key = "prefixfolder/terraform.tfstate"
  region = "us-east-1"
  }
}



#If we need to lock terraform state file use Dynamo db table

terraform {
backend  "s3" {
  bucket = "terraform-state_bucket"
  key = "prefixfolder/terraform.tfstate"
  region = "us-east-1"
  dynamodb_table = "dynamodb-state-locking"
  }
}

#While creating table Key should be LockID
