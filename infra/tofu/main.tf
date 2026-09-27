# Never applied. Orientation declarations only; see ../README.md.
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
  }
}
provider "azurerm" {
  features {}
}
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "ssh_public_key" { type = string }
variable "prefix" {
  type    = string
  default = "codexsynthetic"
}
resource "azurerm_resource_group" "pilot" {
  name     = var.resource_group_name
  location = var.location
}
resource "azurerm_storage_account" "data" {
  name                     = "${var.prefix}data"
  resource_group_name      = azurerm_resource_group.pilot.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}
resource "azurerm_service_plan" "functions" {
  name                = "${var.prefix}-plan"
  resource_group_name = azurerm_resource_group.pilot.name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "Y1"
}
resource "azurerm_linux_function_app" "publish" {
  name                          = "${var.prefix}-publish"
  resource_group_name           = azurerm_resource_group.pilot.name
  location                      = var.location
  service_plan_id               = azurerm_service_plan.functions.id
  storage_account_name          = azurerm_storage_account.data.name
  storage_uses_managed_identity  = true
  https_only                    = true
  identity { type = "SystemAssigned" }
  site_config {
    application_stack {
      python_version = "3.11"
    }
  }
}
resource "azurerm_virtual_network" "pilot" {
  name                = "${var.prefix}-network"
  resource_group_name = azurerm_resource_group.pilot.name
  location            = var.location
  address_space       = ["10.42.0.0/16"]
}
resource "azurerm_subnet" "private" {
  name                 = "private"
  resource_group_name  = azurerm_resource_group.pilot.name
  virtual_network_name = azurerm_virtual_network.pilot.name
  address_prefixes     = ["10.42.1.0/24"]
}
resource "azurerm_network_interface" "vm" {
  name                = "${var.prefix}-nic"
  resource_group_name = azurerm_resource_group.pilot.name
  location            = var.location
  ip_configuration {
    name                          = "private"
    subnet_id                     = azurerm_subnet.private.id
    private_ip_address_allocation = "Dynamic"
  }
}
resource "azurerm_linux_virtual_machine" "vm" {
  name                            = "${var.prefix}-vm"
  resource_group_name             = azurerm_resource_group.pilot.name
  location                        = var.location
  size                            = "Standard_B1s"
  admin_username                  = "pilot"
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.vm.id]
  admin_ssh_key {
    username   = "pilot"
    public_key = var.ssh_public_key
  }
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }
  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }
}
