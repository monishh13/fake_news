$ErrorActionPreference = "Stop"

Write-Host "Setting up environment variables for Java and Node..."
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "1. Setting up Maven..."
if (!(Test-Path "maven\apache-maven-3.9.6\bin\mvn.cmd")) {
    Invoke-WebRequest -Uri "https://archive.apache.org/dist/maven/maven-3/3.9.6/binaries/apache-maven-3.9.6-bin.zip" -OutFile "maven.zip"
    Expand-Archive -Path "maven.zip" -DestinationPath "maven" -Force
    Remove-Item "maven.zip"
}
$MavenPath = "$pwd\maven\apache-maven-3.9.6\bin"
Write-Host "Maven ready at $MavenPath"

Write-Host "2. Starting ML Service in a new window..."
# Use python directly if they have it, or rely on system path
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd ml-service; pip install -r requirements.txt; python -m uvicorn main:app --host 0.0.0.0 --port 8000"

Write-Host "3. Starting Frontend in a new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm install; npm run dev"

Write-Host "4. Starting Backend in a new window..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; `$env:Path += ';$MavenPath'; mvn spring-boot:run"

Write-Host "All 3 services are booting up in separate windows!"
Write-Host "Wait a moment for them to install dependencies and start."
Write-Host "Frontend will be available at http://localhost:5173"
