// Never applied. Orientation declarations only; see ../README.md.
param location string = resourceGroup().location
param prefix string = 'codexsynthetic'
param sshPublicKey string

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${prefix}data'
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: { minimumTlsVersion: 'TLS1_2', allowBlobPublicAccess: false }
}
resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${prefix}-plan'
  location: location
  kind: 'linux'
  sku: { name: 'Y1', tier: 'Dynamic' }
  properties: { reserved: true }
}
resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: '${prefix}-publish'
  location: location
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      appSettings: [
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'AzureWebJobsStorage__accountName', value: storage.name }
      ]
    }
  }
}
resource network 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: '${prefix}-network'
  location: location
  properties: {
    addressSpace: { addressPrefixes: ['10.42.0.0/16'] }
    subnets: [{ name: 'private', properties: { addressPrefix: '10.42.1.0/24' } }]
  }
}
resource nic 'Microsoft.Network/networkInterfaces@2023-11-01' = {
  name: '${prefix}-nic'
  location: location
  properties: {
    ipConfigurations: [{ name: 'private', properties: {
      privateIPAllocationMethod: 'Dynamic'
      subnet: { id: resourceId('Microsoft.Network/virtualNetworks/subnets', network.name, 'private') }
    } }]
  }
  dependsOn: [network]
}
resource vm 'Microsoft.Compute/virtualMachines@2023-09-01' = {
  name: '${prefix}-vm'
  location: location
  properties: {
    hardwareProfile: { vmSize: 'Standard_B1s' }
    osProfile: {
      computerName: 'synthetic-vm'
      adminUsername: 'pilot'
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: { publicKeys: [{ path: '/home/pilot/.ssh/authorized_keys', keyData: sshPublicKey }] }
      }
    }
    storageProfile: {
      imageReference: { publisher: 'Canonical', offer: '0001-com-ubuntu-server-jammy', sku: '22_04-lts-gen2', version: 'latest' }
      osDisk: { createOption: 'FromImage', managedDisk: { storageAccountType: 'Standard_LRS' } }
    }
    networkProfile: { networkInterfaces: [{ id: nic.id }] }
  }
}
