terraform {
  backend "s3" {
    bucket       = "baip-dev-terraform-state-695331051647"
    key          = "environments/dev/terraform.tfstate"
    region       = "us-east-1"
    profile      = "baip-dev"
    encrypt      = true
    use_lockfile = true
  }
}