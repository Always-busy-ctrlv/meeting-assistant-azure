# Azure deployment script for Meeting Assistant

# Parameters
$resourceGroupName = "meeting-assistant-rg"
$location = "centralindia"  # Changed to match your Azure Speech region
$appServiceName = "meeting-assistant-app"
$sqlServerName = "meeting-assistant-sql"
$sqlDatabaseName = "meetings"
$sqlAdminUsername = "sqladmin"
$sqlAdminPassword = (New-Guid).ToString() # Generate a secure random password

# Function to wait for resource creation
function Wait-ForResource {
    param (
        [string]$ResourceType,
        [string]$ResourceName,
        [string]$ResourceGroup
    )
    Write-Host "Waiting for $ResourceType $ResourceName to be ready..."
    $maxAttempts = 30
    $attempt = 0
    while ($attempt -lt $maxAttempts) {
        $resource = az $ResourceType show --name $ResourceName --resource-group $ResourceGroup 2>$null
        if ($resource) {
            Write-Host "$ResourceType $ResourceName is ready!"
            return $true
        }
        $attempt++
        Start-Sleep -Seconds 10
    }
    Write-Host "Timed out waiting for $ResourceType $ResourceName"
    return $false
}

# Create Resource Group
Write-Host "Creating Resource Group..."
az group create --name $resourceGroupName --location $location

# Create App Service Plan (B1 tier)
Write-Host "Creating App Service Plan..."
az appservice plan create --name "${appServiceName}-plan" --resource-group $resourceGroupName --sku B1 --is-linux

# Wait for App Service Plan
Wait-ForResource -ResourceType "appservice plan" -ResourceName "${appServiceName}-plan" -ResourceGroup $resourceGroupName

# Create Web App
Write-Host "Creating Web App..."
az webapp create --name $appServiceName --resource-group $resourceGroupName --plan "${appServiceName}-plan" --runtime "PYTHON:3.9"

# Wait for Web App
Wait-ForResource -ResourceType "webapp" -ResourceName $appServiceName -ResourceGroup $resourceGroupName

# Create SQL Server
Write-Host "Creating SQL Server..."
az sql server create --name $sqlServerName --resource-group $resourceGroupName --location $location --admin-user $sqlAdminUsername --admin-password $sqlAdminPassword

# Wait for SQL Server
Wait-ForResource -ResourceType "sql server" -ResourceName $sqlServerName -ResourceGroup $resourceGroupName

# Create SQL Database (Basic tier)
Write-Host "Creating SQL Database..."
az sql db create --name $sqlDatabaseName --resource-group $resourceGroupName --server $sqlServerName --edition Basic

# Configure firewall rules for SQL Server
Write-Host "Configuring SQL Server firewall rules..."
az sql server firewall-rule create --resource-group $resourceGroupName --server $sqlServerName --name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0

# Get SQL Server connection string
$sqlConnectionString = "Server=tcp:$sqlServerName.database.windows.net,1433;Initial Catalog=$sqlDatabaseName;Persist Security Info=False;User ID=$sqlAdminUsername;Password=$sqlAdminPassword;MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"

# Configure App Service settings
Write-Host "Configuring App Service settings..."
$appSettings = Get-Content -Raw -Path "appsettings.json" | ConvertFrom-Json
$appSettings | Get-Member -MemberType NoteProperty | ForEach-Object {
    $name = $_.Name
    $value = $appSettings.$name
    if ($name -eq "DATABASE_CONNECTION_STRING") {
        $value = $sqlConnectionString
    }
    az webapp config appsettings set --name $appServiceName --resource-group $resourceGroupName --settings "$name=$value"
}

# Configure Python version and startup command
Write-Host "Configuring Python version and startup command..."
az webapp config set --name $appServiceName --resource-group $resourceGroupName --linux-fx-version "PYTHON:3.9"
az webapp config set --name $appServiceName --resource-group $resourceGroupName --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app"

# Enable WebSocket support
Write-Host "Enabling WebSocket support..."
az webapp config set --name $appServiceName --resource-group $resourceGroupName --web-sockets-enabled true

Write-Host "Deployment completed successfully!"
Write-Host "SQL Server Password: $sqlAdminPassword"
Write-Host "Please save this password securely as it won't be shown again!" 